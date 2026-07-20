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

## MCP Server:
Running the MCP server once through MCP Inspector, confirming the five exposed tool names and schemas.
<img width="711" height="378" alt="image" src="https://github.com/user-attachments/assets/e6794552-952f-48df-a383-31009ed15f09" />
<img width="705" height="375" alt="image" src="https://github.com/user-attachments/assets/bf9cd3eb-474f-4de1-a985-ebdb77087a39" />

## Running safe verification calls to confirm tools:

1. search_application
 
  <img width="493" height="439" alt="image" src="https://github.com/user-attachments/assets/ed35d6f9-d4db-48bd-b38c-758f433de114" />
  <img width="543" height="449" alt="image" src="https://github.com/user-attachments/assets/818cbae8-5ae3-45bb-8eb6-45000781521f" />
  <img width="557" height="559" alt="image" src="https://github.com/user-attachments/assets/5e2a87b0-593a-4799-b8e5-ff47da935360" />

2. get_application
   <img width="601" height="318" alt="image" src="https://github.com/user-attachments/assets/467f7119-2cfe-4142-b13c-777ccb056f2c" />
   <img width="559" height="566" alt="image" src="https://github.com/user-attachments/assets/2b26edb0-39fb-441f-9f62-66c906961232" />
   <img width="525" height="557" alt="image" src="https://github.com/user-attachments/assets/49bffcdf-e9d2-408f-a662-4e5dd8a23b97" />

3. cycle_summary
   <img width="585" height="330" alt="image" src="https://github.com/user-attachments/assets/924ff834-8cdd-47b3-858e-7f219d2a1398" />
   <img width="535" height="412" alt="image" src="https://github.com/user-attachments/assets/63eea109-efb7-46f0-a727-6235c2c58262" />
 
4. reviewer_workload_summary
   <img width="508" height="524" alt="image" src="https://github.com/user-attachments/assets/d01a8df9-178b-4971-b8f2-6fdf38d09e84" />

5. reassign_reviewer
   <img width="575" height="426" alt="image" src="https://github.com/user-attachments/assets/4a1c46ef-9475-4c78-a519-c32ee17e03ed" />
   <img width="581" height="286" alt="image" src="https://github.com/user-attachments/assets/d0027b80-0f30-4833-a023-6a64cf6603ff" />
   <img width="568" height="493" alt="image" src="https://github.com/user-attachments/assets/13d3f031-4b31-414c-bbbe-6249808d9acb" />
   <img width="524" height="269" alt="image" src="https://github.com/user-attachments/assets/555c7adc-c9d9-4bc1-9f62-7b5a628727d1" />




  
 

