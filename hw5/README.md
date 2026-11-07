# Campus Customs Desk

A five-agent team that works the open tickets for Campus Customs, a small Yale swag shop. **Handsome Dan** is the boss. He sends four specialist agents (inventory, accounting, facilities, customer service) to look things up through one MCP server over a SQLite database. The agents only prepare; a person approves every payment and closes every ticket on a Yale-themed React board.

Repo: https://github.com/katiebays/mgt409-hw5-campus-customs

## What is here

| Path | What it is |
|---|---|
| `mcp_server/` | The FastMCP server (`server.py`) with 12 tools over the shop database. See its `README.md`. |
| `backend/` | FastAPI app (`main.py`), data types (`models.py`), one prompt per agent in `prompts/`, and the agent code. |
| `frontend/` | The React, Vite and TypeScript dashboard. |
| `data/` | `campus_customs.db` is the original. `campus_customs_new.db` is the working copy, left in its finished state: all 3 tickets resolved, checking at $160.00. |
| `output/` | `harness.md` (everything in one place), `design.md`, `desk_tickets.html` (plan vs actual, cash, reflection), `resolved_board.html` (a board screenshot per ticket), `resolved_tickets.json`, `mcp_smoke.json`, `audit_trail.json`, `github_url.txt`. |
| `AI_prompts.md` | Every prompt used, by problem. |

`backend/` holds more than `main.py` and `models.py` because the agent code lives there: `boss.py`, `specialists.py`, `mcp_client.py`, `audit.py`, `live.py`, `shopdb.py`, `config.py` and a command-line runner, `run.py`.

## Run it

You need Python 3.12 or newer and Node 20 or newer. Run these from this `hw5` folder.

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
```

Open `.env` and set `PORTKEY_API_KEY`. The key is only needed to run the agents; the board, tickets, balance and approvals work without it. `OPENAI_MODEL` defaults to `gpt-5.6-luna`. The real `.env` is never committed.

Start the back end (port 8000), then the board (port 5173), in two terminals:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Pick a ticket and press **Throw it to Handsome Dan**. The working database is already at the end of the full run, so press **Fresh run** (or `POST http://localhost:8000/api/reset`) to put it back to the original values first. Interactive API docs are at http://localhost:8000/docs.

Optional: `python backend/run.py` works every open ticket from the command line, and `.mcp.json` registers the MCP server for Claude Code.

## Safety in one paragraph

Agents never pay, never close a ticket and never send a message. Payments are blocked in code unless a named person approves on the board, every step goes to `output/audit_trail.json`, and customer replies are saved as drafts. The full list is in `output/harness.md`.
