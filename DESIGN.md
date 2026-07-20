# Design decisions

## Choices and boundaries

- I chose Python because it produces a small, readable MCP + MongoDB implementation quickly. The production Node/TypeScript context would be a good reason to choose TypeScript for a long-lived team service, but it is not needed to demonstrate the design here.
- FastMCP provides the protocol boundary and JSON schemas from Python signatures. Pydantic validates the more nuanced search input. PyMongo is synchronous because the agent loop is sequential.
- `search_applications` is a bounded list endpoint with only agent-useful summary fields. `get_application` handles the detailed relational view. `cycle_summary` is the aggregate endpoint. `reassign_reviewer` is the only mutation endpoint.
- The supplied reviewer-max question has no possible data path through the four requested tools, so I added one intentionally narrow, read-only workload-summary tool rather than expose arbitrary reviewer queries or let the model guess.
- Applications reference reviewers and reviews reference applications. These relationships change independently and are queried in different directions, so references are preferable to embedding. `get_application` uses two small queries for reviews/reviewers rather than a complicated lookup pipeline; the summary tool uses aggregation where it materially matters.
- I skipped LangChain/LangGraph and custom orchestration. A plain tool-use loop is easier to inspect and sufficient until multi-step branching or multi-agent work is actually needed.

## Safe reassignment

- Default is a dry run. The preview contains exact application IDs plus before/after reviewer-ID arrays and writes nothing.
- At least `cycle_id` or `status_filter` is mandatory, preventing an unscoped historical reassignment.
- A commit needs an `expectedCount` equal to a freshly recomputed match count, preventing an old preview from authorizing a different scope after data changes. This is deliberately structured data rather than a terminal `input()` prompt, which would block an MCP stdio session.
- Commits above `MAX_REASSIGN` (50) are rejected. Larger changes must be deliberately partitioned.
- Both reviewer workload counters and applications update in a Mongo transaction on replica-set deployments. Local standalone MongoDB falls back to sequential writes and clearly returns `non_atomic_fallback`.
- Residual risks: the count match is not a cryptographic confirmation token; a write can still race after its check, and standalone fallback may partially apply after a process failure. Production would require replica sets, authorization/audit logs, a signed expiring preview token, idempotency keys, and a human approval path for significant batches. The preview-first approach mirrors dry-run/safety modes used for destructive operations.

## Evaluation

`evals/golden_set.json` holds eight representative natural-language cases, including empty results, range filters, a detail retrieval, and a write preview. `run_evals.py` calls the live agent, checks required expected text, and prints accuracy, latency, and token counts. This is deliberately simple enough for CI and needs an explicit API key.

In production I would record structured tool traces; validate tool choice and arguments separately from final-answer correctness; sample answers for hallucination review; track p50/p95 latency, token cost, error rate, and refusal rate; version prompts/models/data fixtures; detect drift; and block deployment on regression thresholds. Structured traces can later feed a proper observability platform.

## Scaling and limitations

- At 50–100 tools, tool descriptions will consume context and routing accuracy will fall. Group tools by domain, retrieve a small relevant tool subset, and keep schemas consistent.
- At 10,000× data, add compound indexes (`cycleId,status`, `assignedReviewerIds`, and requested amount as appropriate), cursor pagination, aggregation limits, caching, and background analytics. Avoid returning long preview diffs; provide a capped sample plus a secured export.
- Current authentication and authorization are intentionally absent for the exercise. A real MCP deployment needs caller identity, tenant/cycle authorization, rate limits, and redacted PII.

## If the backend were federated GraphQL

MCP tools would remain task-oriented rather than mirror every GraphQL field. A tool service would call the composed graph using persisted, allow-listed operations and compose only the subgraph fields needed for each answer. Tool schemas would be stable even when graph ownership changes. Mutations would carry optimistic-concurrency versions, permission checks, audit context, and the same preview/confirmation model. GraphQL query depth/cost limits and error normalization would protect the agent boundary.

## Plain-English rules that gate outcomes

The LLM should translate prose into a constrained, typed rule IR such as `all(status == "complete", score >= 8)`, never execute generated code or issue direct production writes. Show the normalized rule, plain-language explanation, examples/counterexamples, and an impact simulation before activation. Validate types, tenant permissions, and prohibited fields; run a deterministic rules engine; require human approval and test-suite checks for activation; version every change with rollback and audit history. I would explicitly refuse LLM-authored executable code, autonomous rule activation for high-impact outcomes, and direct applicant decisions without deterministic validation and accountable human review.
