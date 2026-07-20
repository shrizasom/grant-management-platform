# Take-Home Assignment — AI Automation Engineer
### WizeHive (a Submittable subsidiary)

Hi Shriza — thanks for your time so far. This exercise is how we get a real feel for how you build and, just as importantly, how you *reason about the choices you make*. When you come in on Wednesday, most of our conversation will be about **this assignment**: we'll ask you to walk us through your code, defend your design decisions, and talk through what you'd do differently or next.

Please read the whole brief before starting.

---

## Ground rules (please read — they matter to us)

- **Time-box: 5–8 hours.** We mean it. This is deliberately scoped so a strong engineer can do a *good, defensible* version in that window. **Do not gold-plate.** A partial solution with clear reasoning beats a complete solution you can't explain.
- **We care about judgment over completeness.** If you run out of time on a part, stop and write down *what you'd do next and why* in your design doc. That write-up counts for as much as working code.
- **Use whatever AI tooling you normally use** — Claude, Cursor, Copilot, etc. This is an AI role; we'd be surprised if you didn't. The one rule: **you must fully understand and be able to defend every line you submit.** On Wednesday we'll ask "why is this here?" about specific pieces. "The tool wrote it" is not an answer we can score.
- **Pick your own language:** Python *or* TypeScript/Node. Choose the one that lets you do your best work — but be ready to explain the choice (our production stack is Node/TypeScript, for context).
- **Scope creep is a negative signal here, not a positive one.** We're evaluating your ability to make good trade-offs under a real constraint.

---

## Scenario

You're joining a team that builds a grant-management platform. We want to safely expose our data to LLM agents so that engineers, support, and eventually customers can ask questions and take actions in plain language — **without giving an agent unguarded write access to production data.**

We've given you a small slice of that domain as a dataset (see `/data`). It models a real grant-review workflow:

- **`programCycles`** — funding rounds (grants, scholarships, fellowships); some active, some closed.
- **`applications`** — submitted applications, each tied to a cycle, with a `status`, a `requestedAmount`, and a list of `assignedReviewerIds`.
- **`reviewers`** — people who score applications; each has an `activeAssignmentsCount`.
- **`reviews`** — a reviewer's score/recommendation/comments on an application.

The data is provided as JSON-lines files. Set up MongoDB however is easiest for you (local Docker or a free Atlas cluster) and load them — e.g.:

```bash
mongoimport --db grants --collection applications  --file data/applications.json
mongoimport --db grants --collection reviews       --file data/reviews.json
mongoimport --db grants --collection reviewers     --file data/reviewers.json
mongoimport --db grants --collection programCycles --file data/programCycles.json
```

(If you'd rather seed it another way, that's fine — just include your seed step in the README.)

---

## What to build

### Part 1 — An MCP server exposing this data (core of the exercise)

Build a **Model Context Protocol server** that exposes the dataset to an LLM agent through a small, well-designed set of tools. We want to see how you think about tool boundaries, schemas, and safety — not how many tools you can produce.

Implement **four tools**:

1. **`search_applications`** — query applications by filters (e.g., status, cycle, requested-amount range). Think about result shaping, limits/pagination, and what an agent actually needs back versus a raw document dump.

2. **`get_application`** — return a single application *with its related data* (its reviews, and the names of assigned reviewers). This one is about how you handle relationships across collections.

3. **`cycle_summary`** — return an aggregate view for a cycle (e.g., counts by status, average review score, total requested amount). Show us you can do real aggregation, not just fetch-and-count-in-app.

4. **`reassign_reviewer`** — a **write** tool that reassigns applications from one reviewer to another (e.g., someone goes on leave, move their in-flight assignments). **This tool can modify many records at once.** How you make this safe is a central thing we're evaluating (see below).

For each tool, we'll be looking at: clear input/output **schemas**, descriptions an LLM can actually route on, **structured and appropriately-shaped** return values, and **error handling**.

> **Safety requirement for the write tool.** A previous version of a similar internal tool once modified thousands of records unintentionally. Design `reassign_reviewer` so that *cannot happen by accident.* At minimum we expect a **dry-run / preview mode** that reports exactly what *would* change (and how many records) before anything is written, plus whatever other guardrails you think belong here. Be prepared to defend your design on Wednesday.

### Part 2 — A minimal agent + an eval harness

1. **A minimal agent** that uses your tools to answer natural-language questions. Wire it up with an LLM (any provider) using function/tool calling — a simple loop is fine; use an orchestration framework only if you can justify it. It should correctly handle at least these:
   - "How many applications in the Community Health Fund cycle are still under review?"
   - "Which reviewer has the most active assignments?"
   - "Show me approved applications requesting more than $10,000."

2. **An eval harness.** This is not optional and we weight it heavily. Build a small, *automated* way to check that your agent/tools produce correct results on a **golden set** of a handful of question→expected-answer cases. Report at least a correctness metric. We're looking for a real evaluation loop — something you could run in CI and grow — not manual spot-checking. If you'd measure more in production (latency, cost, tool-call correctness, hallucination), wire in what you can and describe the rest.

### Part 3 — Design & decision document (`DESIGN.md`)

This is where a lot of the interview will come from. Keep it tight — bullet points are fine. Cover:

- **Choices & trade-offs:** language/framework, your tool boundaries (why these four, why not more/fewer/different), your data-model reasoning (where you'd embed vs. reference, and why), and *anything you deliberately chose not to do.*
- **The write tool:** how you made `reassign_reviewer` safe, and what could still go wrong.
- **Evals:** how your harness works and how you'd extend it for a production LLM system (hallucination, latency, cost, drift, regression gating).
- **Scaling & limitations:** what breaks when the tool catalog grows to 50–100 tools, or when the data is 10,000× bigger. What are the known weaknesses of what you built?
- **Two "if this were production" questions** (write-up only — do *not* build these, we just want your thinking):
  1. Instead of hitting MongoDB directly, imagine the data lives behind a **federated GraphQL API** (multiple subgraphs composed into one graph). How would you expose *that* to an agent, and how does it change your tool design?
  2. We want customers to create workflow rules in **plain English** instead of a rigid rule DSL — the rules gate real applicants' outcomes. How would you build that so it's trustworthy? What would you refuse to let the LLM do directly?

---

## Deliverables

- A **Git repo** (GitHub link preferred; a zip is fine) containing your code.
- A **`README.md`** with setup + run instructions (including how you seeded the data) — we should be able to run it.
- Your **`DESIGN.md`**.
- Optional: a short note or Loom if you want to narrate anything. Not required.

Please have it submitted by **end of day Tuesday** so we can review before Wednesday.

---

## How we'll evaluate (so there are no surprises)

We're assessing, roughly in priority order:

1. **MCP & tool design** — Did you build a real server with well-shaped tools, or just wrap raw queries?
2. **Safety on the write path** — Is the destructive tool genuinely hard to misuse?
3. **Evaluation rigor** — Is there a real, automated eval loop, and do you understand *why* it matters?
4. **Fundamentals** — Data modeling, aggregation, error handling, clean code.
5. **Judgment & communication** — Clear trade-offs, honest limitations, good scoping under the time-box.

We'd genuinely rather see a smaller thing done thoughtfully with a sharp `DESIGN.md` than a sprawling submission. Looking forward to Wednesday — come ready to defend your choices.
