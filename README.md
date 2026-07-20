# Grant Workflow MCP Server

A small Python MCP server for safely querying grant applications and previewing or committing scoped reviewer reassignments. It was built for the WizeHive take-home exercise.

## Stack

- Python, FastMCP, Pydantic, and PyMongo
- MongoDB in Docker for local data
- Anthropic tool-use loop for the optional natural-language agent
- A JSON golden set and runnable evaluation script

## Setup

1. Create an environment and install dependencies:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   Copy-Item .env.example .env
   ```

2. Start MongoDB and seed the supplied JSON-lines files:

   ```powershell
   docker compose up -d
   .\scripts\seed.ps1
   ```

   The seed script requires the [MongoDB Database Tools](https://www.mongodb.com/try/download/database-tools) `mongoimport` executable. Source data remains in `candidate_packet/data/`; this avoids maintaining a duplicate copy.

3. Start the MCP server over stdio:

   ```powershell
   python -m server.mcp_server
   ```

## Agent and evaluations

Set `ANTHROPIC_API_KEY` in `.env`, then run:

```powershell
python -m evals.run_evals
```

The runner prints pass/fail per golden question, aggregate accuracy, per-question latency, and total input/output tokens. It intentionally exits rather than pretending to evaluate if no API key is configured.

Run the lightweight validation tests with `pytest`.

## Tools

The four required tools are `search_applications`, `get_application`, `cycle_summary`, and `reassign_reviewer`. A very narrow read-only `reviewer_workload_summary` helper is included because the required agent question ("Which reviewer has the most active assignments?") cannot be answered from the four specified data paths. It prevents the agent from guessing or receiving raw reviewer documents.

`reassign_reviewer` is preview-first: `dry_run=True` by default, a cycle or status scope is mandatory, commit requires the exact preview count, and commits over 50 records are rejected. The MCP server never prompts on standard input; confirmation is supplied through the structured `expectedCount` field so an agent session cannot hang. See [DESIGN.md](DESIGN.md) for residual risks.
