"""Campus Customs desk: the back end the React dashboard calls.

Start it from this folder:
  uvicorn main:app --reload --port 8000
then the routes below answer at http://localhost:8000 (interactive docs at /docs).

Agents only prepare: they look, plan, draft and update tickets. The one route that moves money is
POST /api/approve, and it runs only after a human clicks Approve.
"""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

import audit
import live
import shopdb
from boss import run_team
from config import DEFAULT_DB, MODEL_NAME, ORIGINAL_DB
from mcp_client import call_mcp_tool
from models import (
    ApproveRequest,
    ApproveResponse,
    CashResponse,
    EventOut,
    EventsResponse,
    LiveEvent,
    LiveResponse,
    PaymentOut,
    PaymentsResponse,
    ResetResponse,
    ResolveRequest,
    ResolveResponse,
    RunTicketResponse,
    TicketOut,
    TicketsResponse,
)

app = FastAPI(title="Campus Customs desk", version="1.0.0")

# The dashboard runs on another local port (Vite uses 5173), so allow local pages to call in. Nothing else.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

_running: set[int] = set()  # tickets the agent team is working right now


def _ticket_out(row: dict) -> TicketOut:
    pending = shopdb.pending_payments(row)
    return TicketOut(
        **row,
        state="resolved" if row["status"] == "resolved" else "open",
        running=row["id"] in _running,
        pending_payments=pending,
        has_draft_reply="DRAFT REPLY" in (row["notes"] or ""),
        can_close=row["status"] in ("in_progress", "waiting_on_approval") and not pending,
    )


def _counts() -> tuple[int, int]:
    rows = shopdb.list_tickets()
    done = sum(1 for r in rows if r["status"] == "resolved")
    return len(rows) - done, done


@app.get("/api/health")
def health():
    """Is the back end up, which database and model it uses, and whether the Portkey key is set."""
    return {
        "ok": True,
        "database": DEFAULT_DB.name,
        "model": MODEL_NAME,
        "portkey_key_set": bool(os.getenv("PORTKEY_API_KEY", "").strip()),
        "running_tickets": sorted(_running),
    }


@app.get("/api/tickets", response_model=TicketsResponse)
def get_tickets():
    """The tickets, each marked open or resolved (and running while the agents work on it)."""
    tickets = [_ticket_out(r) for r in shopdb.list_tickets()]
    resolved = sum(1 for t in tickets if t.state == "resolved")
    return TicketsResponse(tickets=tickets, open=len(tickets) - resolved, resolved=resolved)


@app.post("/api/tickets/{ticket_id}/run", response_model=RunTicketResponse)
async def run_ticket(ticket_id: int):
    """Run the agent team on one ticket and wait for its report. The agents never pay: no approver is given."""
    row = shopdb.get_ticket(ticket_id)
    if row is None:
        raise HTTPException(404, f"No ticket {ticket_id}.")
    if row["status"] == "resolved":
        raise HTTPException(409, f"Ticket {ticket_id} is already resolved.")
    if ticket_id in _running:
        raise HTTPException(409, f"The agents are already working on ticket {ticket_id}.")
    _running.add(ticket_id)
    try:
        result, run_id = await run_team(
            f"Work ticket {ticket_id} only. Triage it, get it handled by the right departments, "
            "update the ticket, and tell me what needs my approval.",
            approver=None,
            ticket_id=ticket_id,
        )
    except Exception as exc:
        raise HTTPException(500, f"The agent run failed: {type(exc).__name__}: {str(exc)[:300]}") from exc
    finally:
        _running.discard(ticket_id)
    return RunTicketResponse(run_id=run_id, ticket=_ticket_out(shopdb.get_ticket(ticket_id)), result=result)


@app.get("/api/events", response_model=EventsResponse)
def get_events(
    limit: int = Query(50, ge=1, le=500),
    ticket_id: int | None = None,
    run_id: str | None = None,
    since_seq: int | None = Query(None, description="Only events after this seq. Use latest_seq from the last call."),
):
    """Recent agent steps, oldest first: who spoke, what they said, and which tools they used."""
    events, total = audit.read_events(limit=limit, ticket_id=ticket_id, run_id=run_id, since_seq=since_seq)
    return EventsResponse(
        events=[EventOut(**e) for e in events],
        total=total,
        latest_seq=total - 1,
        running_tickets=sorted(_running),
    )


@app.get("/api/live", response_model=LiveResponse)
def get_live(since_seq: int | None = None, ticket_id: int | None = None):
    """Moments from a run as they happen (ticket sent out, specialist sent a task, specialist reported back)."""
    events, latest = live.read(since_seq=since_seq, ticket_id=ticket_id)
    return LiveResponse(events=[LiveEvent(**e) for e in events], latest_seq=latest, running_tickets=sorted(_running))


@app.post("/api/tickets/{ticket_id}/resolve", response_model=ResolveResponse)
async def resolve_ticket(ticket_id: int, body: ResolveRequest):
    """A human reviewed the agents' work (and any drafted reply) and closes the ticket. Agents cannot do this."""
    who = body.approved_by.strip()
    if not who or len(who) > 80:
        raise HTTPException(422, "approved_by must be the approver's name (1 to 80 characters).")
    row = shopdb.get_ticket(ticket_id)
    if row is None:
        raise HTTPException(404, f"No ticket {ticket_id}.")
    if row["status"] == "resolved":
        raise HTTPException(409, f"Ticket {ticket_id} is already resolved.")
    if ticket_id in _running:
        raise HTTPException(409, f"The agents are still working on ticket {ticket_id}.")
    if row["status"] == "open":
        raise HTTPException(409, f"The agents have not worked ticket {ticket_id} yet. Run them first.")
    pending = shopdb.pending_payments(row)
    if pending:
        p = pending[0]
        raise HTTPException(409, f"Approve the {p['kind']} payment of ${p['amount']:.2f} to {p['payee']} first.")
    note = f"Closed by {who}: reviewed the agents' work" + (" and the drafted reply." if "DRAFT REPLY" in (row["notes"] or "") else ".")
    if body.note:
        note += " " + body.note.strip()[:300]
    args = {"ticket_id": ticket_id, "status": "resolved", "note": note, "updated_by": who}
    result = await call_mcp_tool("update_ticket", args)
    audit.log_human_approval(tool="update_ticket", args=args, result=result, approver=who, database=str(DEFAULT_DB), ticket_id=ticket_id)
    if not result.get("ok"):
        raise HTTPException(409, result.get("error", "The ticket could not be closed."))
    return ResolveResponse(ok=True, ticket=_ticket_out(shopdb.get_ticket(ticket_id)))


@app.post("/api/approve", response_model=ApproveResponse)
async def approve(body: ApproveRequest):
    """A human clicked Approve: pay the vendor invoice or the rent. This is the only route that changes cash."""
    who = body.approved_by.strip()
    if not who or len(who) > 80:
        raise HTTPException(422, "approved_by must be the approver's name (1 to 80 characters).")
    tool, args = (
        ("pay_invoice", {"invoice_id": body.ref_id}) if body.kind == "invoice" else ("pay_rent", {"lease_id": body.ref_id})
    )
    args["approved_by"] = who
    ticket = shopdb.get_ticket(body.ticket_id) if body.ticket_id is not None else None
    if body.ticket_id is not None and ticket is None:
        raise HTTPException(404, f"No ticket {body.ticket_id}.")

    result = await call_mcp_tool(tool, args)  # the server enforces: open bill, enough cash, rent due soon, named approver
    audit.log_human_approval(
        tool=tool, args=args, result=result, approver=who, database=str(DEFAULT_DB), ticket_id=body.ticket_id
    )
    if not result.get("paid"):
        raise HTTPException(409, result.get("error", "The payment was refused."))

    if ticket is not None:
        note = f"Payment approved by {who}: {body.kind} {body.ref_id}, ${result['amount']:.2f} paid."
        status = "resolved" if body.resolve_ticket else ticket["status"]
        await call_mcp_tool("update_ticket", {"ticket_id": ticket["id"], "status": status, "note": note, "updated_by": who})
        ticket = shopdb.get_ticket(ticket["id"])
    return ApproveResponse(
        ok=True,
        payment=result,
        checking_balance=shopdb.checking_balance()["balance"],
        ticket=_ticket_out(ticket) if ticket else None,
    )


@app.get("/api/payments", response_model=PaymentsResponse)
def get_payments():
    """Every payment made so far, in order, so the board can draw the cash flow."""
    pays = shopdb.list_payments()
    balance = shopdb.checking_balance()["balance"]
    return PaymentsResponse(
        payments=[PaymentOut(**p) for p in pays],
        starting_balance=round(balance + sum(p["amount"] for p in pays), 2),
        checking_balance=balance,
    )


@app.get("/api/cash", response_model=CashResponse)
def get_cash():
    """The current checking balance, from cash_accounts."""
    return CashResponse(**shopdb.checking_balance())


@app.post("/api/reset", response_model=ResetResponse)
def reset():
    """Put the database back to its original values for a fresh run. The audit trail is kept."""
    if _running:
        raise HTTPException(409, f"Cannot reset while the agents are working on ticket(s) {sorted(_running)}.")
    shopdb.reset_db()
    open_, done = _counts()
    return ResetResponse(
        ok=True,
        restored_from=ORIGINAL_DB.name,
        open=open_,
        resolved=done,
        checking_balance=shopdb.checking_balance()["balance"],
        note="Tickets, cash, bills, rent and payments are back to their original values. output/audit_trail.json is not erased.",
    )
