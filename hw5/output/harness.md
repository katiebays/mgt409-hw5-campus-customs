# Campus Customs Database Harness

Source: `data/campus_customs.db` (SQLite). Nine tables that the agents read and, in a few cases, write. For each field, one sentence on why it matters to the agents.

## `desk` — what "today" is (1 row)

- `date_today` — the agents must use this as the current date, not the computer clock, so due dates and "due in 2 days" are judged against the same day the data describes.
- `notes` — free text for the manager to leave standing instructions or context for the agents (empty right now).

## `cash_accounts` — money on hand (1 row)

- `name` — identifies which account (currently `checking`) a payment would be drawn from, so the agents never pay out of an account that does not exist.
- `balance` — tells the agents whether a bill can actually be paid, which is the main check before any money moves.
- `date` — shows how fresh the balance is, so the agents know whether it reflects today's cash.

## `vendors` — who supplies the shop (3 rows)

- `id` — the key that invoices point to, so every bill can be tied to the right supplier.
- `name` — tells the agents and the manager who is being dealt with or paid.
- `specialty` — what each vendor does (reprints, mugs, courier), which decides who to call to fix a given problem.
- `lead_days` — how many days a vendor needs to deliver, which lets the agents promise customers realistic dates.

## `pricing` — cost and price per product (4 rows)

- `sku` — the product code that links price to stock and to customer requests.
- `unit_cost` — what each item costs the shop, which sets the floor for any discount.
- `list_price` — the normal selling price shown to customers, and the starting point for quoting.

## `inventory` — stock by product and size (10 rows)

- `sku` — the product code that connects each stock row to its price and to tickets.
- `name` — the human-readable product name the agents use when writing to customers.
- `size` — separates stock by size, since a customer asking for size S cannot be filled from size L stock.
- `qty` — how many units are on hand, which decides whether an order can ship now or needs a reprint (0 means sold out).
- `location` — the aisle where the item sits, which tells staff where to pick it from.

## `leases` — the shop's rent (1 row)

- `id` — the key that rent tickets point to, so a notice can be matched to the right lease.
- `space_name` — which space the rent is for, so notices are not confused if there is more than one.
- `landlord` — who gets paid, and who a rent notice should come from.
- `monthly_rent` — the amount to pay, which the agents compare with the cash balance.
- `next_due` — the date rent is due, so the agents can warn about it before it is late.
- `notes` — extra terms or reminders about the lease (empty right now).

## `invoices` — bills from vendors (1 row)

- `id` — the invoice number, used to look up or refer to a specific bill.
- `vendor_id` — links the bill to the vendor who sent it.
- `amount` — how much is owed, the number that would be checked against cash and paid.
- `due_date` — when it must be paid, so the agents can spot a bill that is already overdue.
- `status` — whether the bill is open or paid, which stops the agents from paying the same bill twice.
- `description` — says what the bill is for, so the agents can connect it to an order or product.

## `tickets` — requests the agents work on (3 rows)

- `id` — the ticket number, so each request can be tracked, answered, and logged.
- `type` — the kind of request (customer order, rent notice, price override), which tells the system which agent should handle it.
- `requester` — who sent it, so replies and any approvals go to the right person or organization.
- `subject` — a short title for quick scanning of the queue.
- `sku` — which product the request is about, linking it to stock and pricing.
- `size` — the size requested, needed to check the right inventory row.
- `qty` — how many units are wanted, which sets the order total and whether stock is enough.
- `lease_id` — links a rent notice to its lease so the amount and due date can be checked.
- `invoice_id` — links a ticket to a vendor bill that relates to it, so open costs are not missed.
- `status` — whether the request is still open, so finished work is not repeated.
- `notes` — the request in the sender's own words, which holds details the structured fields miss.
- `created_at` — when the request arrived, so older requests can be handled first and timing can be judged.

## `payments` — record of money paid out (empty)

- `id` — a unique number for each payment, so every payout can be traced.
- `kind` — what type of payment it is (such as an invoice or rent), so spending can be grouped.
- `ref_id` — the invoice or lease being paid, tying the payment back to the bill that caused it.
- `amount` — how much was paid, which must also reduce the cash balance.
- `account` — which cash account the money came from.
- `paid_at` — when it was paid, for the audit trail.
- `approved_by` — who signed off on the payment, so no money moves without a named approver.

# Tables at a glance

Original values, `data/campus_customs.db` (the working copy is `data/campus_customs_new.db`). Field-by-field detail is above.

| Table | Rows | What it holds | Tools that read it | Tools that write it |
|---|---|---|---|---|
| `desk` | 1 | Today's date for the shop (2026-08-31) | almost every tool | none |
| `cash_accounts` | 1 | Checking balance ($3,400.00) | `get_cash_position`, `pay_invoice`, `pay_rent` | `pay_invoice`, `pay_rent` |
| `vendors` | 3 | Suppliers, what they do, lead time | `suggest_restock`, `list_invoices`, `get_ticket`, `get_cash_position` | none |
| `pricing` | 4 | Unit cost and list price per product | `check_order`, `suggest_restock`, `get_stock`, `quote_price`, `get_ticket` | none |
| `inventory` | 10 | Units on hand by product and size | `check_order`, `suggest_restock`, `get_stock`, `get_ticket` | none |
| `leases` | 1 | The shop's rent and due date | `get_lease`, `get_ticket`, `get_cash_position` | `pay_rent` (moves `next_due` forward) |
| `invoices` | 1 | Vendor bills | `list_invoices`, `get_ticket`, `get_cash_position` | `pay_invoice` (marks paid) |
| `tickets` | 3 | Requests the agents work | `list_tickets`, `get_ticket`, `check_order` | `update_ticket` |
| `payments` | 0 | Every payment made (2 rows after the full run) | the back end's `/api/payments` | `pay_invoice`, `pay_rent` |

# The agent team

Five agents work the ticket queue. They get shop facts only from the MCP server in `mcp_server/` (the existing Campus Customs server over `data/campus_customs_new.db`). The boss delegates; the four specialists do the work and report back to the boss. Specialists never talk to each other directly.

Code: `backend/boss.py` (boss and the run), `backend/specialists.py` (the four specialists and their tool lists), `backend/mcp_client.py` (MCP connection and guardrails), `backend/audit.py` (audit trail), `backend/live.py` (live feed for the board), `backend/shopdb.py` (read-only database helpers and reset), `backend/main.py` (the API routes), `backend/models.py` (data types), `backend/prompts/` (one prompt file per agent), `frontend/` (the dashboard). Run it with `python backend/run.py` (add `--approver "Name"` to let payments go through, `--db copy.db` to work on a copy).

## Agents

| Agent | Job | MCP tools it can use | Prompt |
|---|---|---|---|
| **boss** | Reads the queue, hands each ticket to the right specialists, and writes the final report for the manager. It changes nothing itself. | `list_tickets`, `get_ticket`, plus the delegation tools `ask_inventory`, `ask_accounting`, `ask_facilities`, `ask_customer_service` | `prompts/boss.md` |
| **inventory** | Knows what is on the shelves and what to reorder. | `get_ticket`, `get_stock`, `check_order`, `suggest_restock`, `update_ticket` | `prompts/inventory.md` |
| **accounting** | Watches cash, vendor bills and rent, and pays them when a person has approved. | `get_ticket`, `list_invoices`, `get_cash_position`, `pay_invoice`, `pay_rent`, `update_ticket` | `prompts/accounting.md` |
| **facilities** | Looks after the shop lease and checks rent notices against it. It cannot pay. | `get_ticket`, `get_lease`, `get_cash_position`, `update_ticket` | `prompts/facilities.md` |
| **customer service** | Quotes prices, handles discount requests and drafts customer replies. It cannot send them. | `get_ticket`, `list_tickets`, `get_stock`, `check_order`, `quote_price`, `update_ticket` | `prompts/customer_service.md` |

Each agent's loop: the model reads its task, calls tools, reads the results, and repeats until it returns a structured report (`AgentReport`; the boss returns a `TeamResult`). The boss's delegation tools start a full loop for the specialist and return its report.

## MCP tools

"Writes" means the tool changes the database. "New" means added for the agent team.

| Tool | Writes? | Tables it uses | Used by | Why it is valuable |
|---|---|---|---|---|
| `check_order` | no | `tickets`, `inventory`, `pricing` | inventory, customer service | Says whether a customer order can be filled and what it costs, so no one promises stock that is not there. |
| `suggest_restock` | no | `inventory`, `pricing`, `vendors`, `desk` | inventory | Finds sold-out and low items with a vendor, lead time, arrival date and cost, so empty shelves are fixed before customers ask. |
| `pay_invoice` | **yes** | `invoices` (status), `cash_accounts` (balance), `payments` (new row), `desk` | accounting | Pays an overdue bill while blocking double payment, overdrafts and unapproved payments. |
| `list_tickets` (new) | no | `tickets`, `desk` | boss, customer service | Shows the queue, so the boss knows what work exists. |
| `get_ticket` (new) | no | `tickets`, `leases`, `invoices`, `vendors`, `inventory`, `pricing`, `desk` | all five | Gives one ticket with its linked lease, bill and stock, so an agent never works from the email text alone. |
| `update_ticket` (new) | **yes** | `tickets` (status and notes), `desk` | inventory, accounting, facilities, customer service | Records what each agent found or decided on the ticket, signed with the agent's name and the date. |
| `get_stock` (new) | no | `inventory`, `pricing` | inventory, customer service | Gives units on hand and price for any request, such as a bulk order that is not a customer order ticket. |
| `quote_price` (new) | no | `pricing` | customer service | Prices a quantity at a discount and shows margin and the break-even discount, so discount requests are judged on numbers. |
| `list_invoices` (new) | no | `invoices`, `vendors`, `desk` | accounting | Lists vendor bills with days overdue, so the oldest debt is paid first. |
| `get_cash_position` (new) | no | `cash_accounts`, `invoices`, `vendors`, `leases`, `desk` | accounting, facilities | Shows cash, bills and rent due soon, and what is left, so one payment does not starve another. |
| `get_lease` (new) | no | `leases`, `desk` | facilities | Gives rent, due date and days left, so a landlord's notice can be checked against the record. |
| `pay_rent` (new) | **yes** | `leases` (next_due), `cash_accounts` (balance), `payments` (new row), `desk` | accounting | Pays rent that is due within 7 days, with approval and enough cash, and moves the next due date forward. |

## Audit trail

Every step of every agent's loop is appended to `output/audit_trail.json` as it finishes. An entry holds: run id (one per team run), agent, agent run id, parent agent run id (the boss's, for delegated work), step number, UTC time, the task, model, database file, the human approver (or null), any text the model wrote, every tool call with its arguments and result (cut to 600 characters), guardrail events, why the step ended, and token counts. The file is a JSON list; new entries are added at the end and earlier bytes are never rewritten. If the file is not a valid list, the code refuses to touch it.

# Back-end routes

`backend/main.py` is a FastAPI app. From the `backend` folder run `uvicorn main:app --reload --port 8000`, and the routes answer at `http://localhost:8000` (interactive docs at `/docs`). Pages on `localhost` or `127.0.0.1` (such as the dashboard on port 5173) are allowed to call it.

| Method | URL | What it does |
|---|---|---|
| GET | `/api/health` | Shows the back end is up, which database and model it uses, and which tickets the agents are working on. |
| GET | `/api/tickets` | Returns the 3 tickets, each marked `open` or `resolved`, with any unpaid linked payment, whether a draft reply exists, and whether it can be closed. |
| POST | `/api/tickets/{ticket_id}/run` | Runs the agent team on that ticket and returns its report; the agents prepare but never pay or close. |
| GET | `/api/events` | Returns recent agent steps, what each agent said and which tools it used, oldest first; filter with `ticket_id`, `run_id`, `limit`, or `since_seq` to refresh. |
| GET | `/api/live` | Returns the moments of a run as they happen (ticket sent out, specialist sent a task, specialist reported back), which the board animates. |
| POST | `/api/approve` | After a human clicks Approve, pays a vendor invoice or the rent through the MCP server; this is the only route that changes cash. |
| POST | `/api/tickets/{ticket_id}/resolve` | After a human reviews the work and any drafted reply, closes the ticket; refused while a linked payment is unpaid. |
| GET | `/api/cash` | Returns the current checking balance from `cash_accounts`. |
| GET | `/api/payments` | Returns every payment so far, in order, with payee and ticket, so the board can draw the cash flow. |
| POST | `/api/reset` | Puts the database back to its original values for a fresh run (the audit trail is kept). |

Notes on how they behave:

- A ticket shows `resolved` only when its status is `resolved`; `in_progress` and `waiting_on_approval` still show as `open` on the board (the real status is returned too).
- `/api/approve` takes `kind` (`invoice` or `rent`), `ref_id` (the invoice or lease id), `approved_by` (the person who clicked), and optionally `ticket_id` and `resolve_ticket`. Paying a vendor invoice is how a purchase is approved, since a reorder becomes a vendor bill. It goes through `pay_invoice` or `pay_rent`, so every payment check still applies, and a refused payment returns 409 with the reason.
- Each approval or close, whether it worked or was refused, is written to `output/audit_trail.json` as an entry from `human` with the approver's name.
- Events and live moments carry a sequence number. Pass the last one back as `since_seq` to get only what is new.
- `/api/reset` copies `data/campus_customs.db` over the working `data/campus_customs_new.db`. It refuses while an agent run is in progress.

# Dashboard

The board is a React, Vite and TypeScript app in `frontend/`. Start it with `npm run dev` and open `http://localhost:5173` (the back end must be running on port 8000, which is where the board's calls go; it can be changed with `VITE_API_URL`). It is themed Yale blue, with Handsome Dan as the boss. `output/design.md` explains the look and why.

| On the screen | What it shows | Routes it uses |
|---|---|---|
| Tickets list | All 3 tickets with open, working, waiting-for-you or resolved states; pick one and press Throw | `GET /api/tickets`, `POST /api/tickets/{id}/run` |
| The field | The ticket as a tennis ball; Handsome Dan fetches it, throws it to a specialist pup, who runs to it and brings it back with a report | `GET /api/live` |
| What each agent did | One card per agent with a short summary and the tools it used; agents not called are dimmed | `GET /api/events` |
| Play by play | Every step, newest first, including the human approvals and guardrail notes | `GET /api/events` |
| Needs your approval | The unpaid purchase or rent, the drafted reply (marked not sent), and a close button | `POST /api/approve`, `POST /api/tickets/{id}/resolve` |
| Checking balance | The balance, a line that redraws after each payment, and a ledger | `GET /api/cash`, `GET /api/payments` |
| Fresh run | Puts the database back to the start | `POST /api/reset` |

A ticket becomes resolved only when a person closes it: either by approving the last payment that clears it (rent), or by approving the drafted reply and pressing close. The board refreshes every second while the agents work and every few seconds otherwise.

# The full run (Problem 9)

The working database was reset first, so checking started at $3,400.00. Tickets were worked on the board in the order 101, 102, 103, and each was resolved. Every agent step is appended to `output/audit_trail.json`.

| Ticket | Agents called | Cash change | Why | Final status |
|---|---|---|---|---|
| 101 Bulldog tee | inventory, accounting, customer service | −$840.00 (3,400.00 → 2,560.00) | Purchase: paid vendor invoice 501 to Bulldog Print Co | resolved |
| 102 Rent due | facilities, accounting | −$2,400.00 (2,560.00 → 160.00) | Rent to Elm City Properties | resolved |
| 103 Bulk hoodie discount | inventory, customer service | $0.00 (160.00 → 160.00) | Proposals only: reorder and discount quote, nothing paid | resolved |

Ending checking balance: **$160.00**, which matches `cash_accounts` in the working database. The itemized math is in the Cache tab of `output/desk_tickets.html`, the per-ticket results in `output/resolved_tickets.json`, and a screenshot of the board for each ticket in `output/resolved_board.html`.

# Safety

A shop that deals with real customers and real money needs these guardrails. The first group is enforced in this build, in code, not just in a prompt. The second group is what a real business would add before going live.

**Enforced now**

- **A person approves every payment.** `pay_invoice` and `pay_rent` are blocked unless the run was started with a named human approver. The code sets `approved_by`; the model cannot pick or invent it.
- **Payment checks in the tool.** The bill must be open, rent must be due within 7 days, cash must cover it, and every payment is recorded with who approved it. Paid bills cannot be paid again.
- **Least privilege.** Each agent only sees the tools it needs. The boss cannot change data, facilities cannot pay, and no agent can send anything.
- **Only a person closes a ticket.** If an agent tries to set a ticket to `resolved`, the code changes it to `waiting_on_approval` and logs it. Closing goes through `POST /api/tickets/{id}/resolve`, and is refused while a linked bill or rent is still unpaid.
- **Customer messages are drafts.** There is no send tool. Replies are saved on the ticket as a draft and the ticket is set to `waiting_on_approval` for a person to review. Prompts forbid putting unit cost, margin or vendor names in a reply.
- **No promises.** Agents may not promise delivery dates, discounts or refunds. Discounts are priced and recommended, never granted.
- **Facts from the database, not memory.** Dates come from the `desk` table, and numbers come from tool results.
- **Limits.** One agent may make at most 12 model requests per turn, and the boss at most 8 delegations per run.
- **Signed, append-only record.** Ticket notes are stamped with the real agent name, and every step is written to the audit trail, including each blocked action.
- **Approvals are named and recorded.** The board asks who is approving, the name goes into `payments.approved_by`, the ticket note and the audit trail, and a refused approval is logged too. In the Problem 9 run Claude clicked Approve on Katie Bays's instruction, and the name says so.
- **Money moves in one place only.** Agents never pay. `POST /api/approve` is the single route that changes cash, it needs the approver's name, and it records that approval in the audit trail.
- **Test on a copy.** `run.py --db` runs the whole team on a copy of the database.

**A real business would also add**

- Real sign-in for the approve route. Today it trusts the name sent with the request and only allows local pages, which is fine on one laptop and not for a real shop.
- Spending limits, and two approvers above a set amount; the approver should not be the person who raised the request.
- An allowlist of payees, so money can only go to known vendors and the landlord.
- A written discount policy with a price floor, and a human sign-off before any discount reaches a customer.
- Treat ticket and email text as untrusted: a customer or "landlord" could write instructions into a ticket. Agents must treat it as data, and unusual requests should be flagged.
- Privacy: keep customer names and contact details out of logs where possible (the audit trail here does contain ticket text), limit who can read it, and set a retention period.
- A review step for customer-facing text for accuracy, tone and legal claims, and a human owner for refunds, complaints and chargebacks.
- Tamper-evident audit storage, backups, and a way to undo a bad change.
- Alerts for odd behavior (many payments, repeated blocked actions), rate limits, and a kill switch that stops all agents at once.
