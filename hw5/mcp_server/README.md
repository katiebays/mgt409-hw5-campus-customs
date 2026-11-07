# Campus Customs MCP Server

## What it is for

This MCP server (built with FastMCP) is how the Campus Customs agents and the vibe coder read and update the shop's database, through a fixed set of safe tools instead of touching the database directly. It is the only source of shop facts for the agent team in `backend/`. Status: built and tested (see `output/mcp_smoke.json`).

## Database

`data/campus_customs_new.db` (SQLite), a copy of `campus_customs.db` so the original stays unchanged. Set the `CAMPUS_CUSTOMS_DB` environment variable to point the server at a different file (the tests and `backend/run.py --db` do this).

## Tools (12)

| Tool | What it does | Tables | Changes data? |
|---|---|---|---|
| `check_order(ticket_id)` | Checks a customer order ticket against stock and price. | `tickets`, `inventory`, `pricing` | no |
| `suggest_restock(low_stock=3, restock_to=10)` | Lists sold-out and low items with vendor, lead time, arrival date and cost. | `inventory`, `pricing`, `vendors`, `desk` | no |
| `pay_invoice(invoice_id, approved_by)` | Pays an open invoice if cash covers it and a person approves. | `invoices`, `cash_accounts`, `payments`, `desk` | **yes** |
| `list_tickets(status="open")` | Lists tickets in the queue. | `tickets`, `desk` | no |
| `get_ticket(ticket_id)` | One ticket with its linked lease, invoice and stock. | `tickets`, `leases`, `invoices`, `vendors`, `inventory`, `pricing`, `desk` | no |
| `update_ticket(ticket_id, status, note, updated_by)` | Sets a ticket's status and appends a dated, signed note. | `tickets`, `desk` | **yes** |
| `get_stock(sku, size=None)` | Units on hand, location and list price. | `inventory`, `pricing` | no |
| `quote_price(sku, qty, discount_pct=0)` | Price, total, margin and break-even discount. Prices only; approves nothing. | `pricing` | no |
| `list_invoices(status="open")` | Vendor bills with days overdue. | `invoices`, `vendors`, `desk` | no |
| `get_cash_position()` | Cash, open bills, rent due within 7 days, and cash left. | `cash_accounts`, `invoices`, `vendors`, `leases`, `desk` | no |
| `get_lease(lease_id)` | A lease with days until rent is due. | `leases`, `desk` | no |
| `pay_rent(lease_id, approved_by)` | Pays rent due within 7 days if cash covers it and a person approves; moves `next_due` forward a month. | `leases`, `cash_accounts`, `payments`, `desk` | **yes** |

The three tools that change money or tickets refuse bad requests (no approver, already paid, not enough cash, rent not yet due, unknown ticket or status). The agent team adds one more rule outside this server: payments only run when the run has a named human approver. See `output/harness.md` for the agents, which tool each can use, and the safety rules.

## Run and connect

- **Install:** from the `hw5` folder, `python -m venv .venv`, activate it, and `pip install -r requirements.txt`. One environment covers this server, the agents and the API.
- **Vibe coder:** registered as `campus-customs` in `.mcp.json`. Open Claude Code in the `hw5` folder with the environment active (so `python` can import fastmcp) and approve the server when asked.
- **Agent team:** `backend/` starts this same server over stdio (`python backend/run.py`).
- **Tests:** `output/mcp_smoke.json` holds every test call with its prompt, tool name, arguments and output. Calls that change data ran on temporary copies, so `data/campus_customs_new.db` is unchanged.
