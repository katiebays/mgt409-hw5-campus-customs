"""Data types for the Campus Customs agent team: reports the agents return, the run request,
the per-run context (deps) each agent carries, and the audit-trail entry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
SPECIALISTS: tuple[str, ...] = ("inventory", "accounting", "facilities", "customer_service")


# ---- what the agents return ----

class AgentReport(BaseModel):
    """What a specialist sends back to the boss when its task is done."""

    summary: str = Field(description="Plain-English result of the task, from tool results only.")
    actions_taken: list[str] = Field(
        default_factory=list, description="Changes actually made through tools (ticket updates, payments)."
    )
    needs_human: list[str] = Field(
        default_factory=list, description="Decisions or approvals only a person can give, each stated as a clear ask."
    )
    ticket_ids: list[int] = Field(default_factory=list, description="Tickets this report is about.")
    status: Literal["done", "needs_approval", "blocked"] = Field(
        description="done: nothing left. needs_approval: waiting on a person. blocked: cannot finish with the tools given."
    )


class TicketOutcome(BaseModel):
    """The boss's one-line verdict on one ticket."""

    ticket_id: int
    status: Literal["resolved", "waiting_on_approval", "in_progress", "blocked"]
    summary: str
    handled_by: list[str] = Field(default_factory=list, description="Specialists who worked on it.")
    needs_human: list[str] = Field(default_factory=list)


class TeamResult(BaseModel):
    """The boss's final answer for a run."""

    answer: str = Field(description="Short summary for the shop manager.")
    outcomes: list[TicketOutcome] = Field(default_factory=list)
    needs_human: list[str] = Field(default_factory=list, description="Everything waiting on a person, in priority order.")


# ---- what goes in ----

class RunRequest(BaseModel):
    """One request to the team."""

    message: str = Field(description="What the manager wants done, in plain words.")
    approver: str | None = Field(
        default=None,
        description="A real person who approves payments for this run. Without one, no money moves.",
    )


# ---- per-run context shared with tools and the audit logger ----

@dataclass
class TeamContext:
    """Facts about one team run. Each agent invocation gets its own copy (its `deps`)."""

    run_id: str  # same for every step of one team run
    agent: AgentName = "boss"
    agent_run_id: str = ""  # unique to this agent invocation
    parent_agent_run_id: str | None = None
    approver: str | None = None  # the human who approved payments; None means payments are blocked
    database: str = ""  # which database file this run used
    task: str = ""  # what this agent was asked
    ticket_id: int | None = None  # the ticket this run is about, when started from the dashboard
    guardrail_events: list[str] = field(default_factory=list)  # notes the audit logger drains after each step
    shared: dict[str, Any] = field(default_factory=dict)  # counters shared across all agents in the run (e.g. delegations)


# ---- audit trail ----

class AuditToolCall(BaseModel):
    """One tool call inside a loop step."""

    tool_name: str
    args: str = Field(description="Arguments the agent sent, as JSON text (cut to 600 characters).")
    result_summary: str = Field(description="What came back, cut to 600 characters.")


class AuditEntry(BaseModel):
    """One step of one agent's loop. Added to output/audit_trail.json as it happens; never edited or removed."""

    run_id: str = Field(description="Same for every step of one team run, so a run can be followed end to end.")
    agent: str
    agent_run_id: str = Field(description="Same for every step of one agent's turn.")
    parent_agent_run_id: str | None = Field(description="The boss's agent_run_id when this agent was delegated to.")
    iteration: int = Field(description="1, 2, 3... within this agent's turn.")
    timestamp: str = Field(description="UTC time the step finished (ISO 8601).")
    task: str = Field(description="What this agent was asked (cut to 300 characters).")
    model: str
    database: str
    approver: str | None = Field(description="The person who approved payments for this run, or null.")
    ticket_id: int | None = Field(default=None, description="The ticket the run was started for, if any.")
    assistant_text: str | None = Field(default=None, description="Any text the model wrote this step (cut to 600).")
    tool_calls: list[AuditToolCall] = Field(default_factory=list)
    guardrail_events: list[str] = Field(default_factory=list, description="Rules the code enforced this step.")
    stop_reason: str = Field(description="'tool_call' (loop continues), 'final_result', or 'error: ...'.")
    input_tokens: int | None = None
    output_tokens: int | None = None


# ---- back-end API (backend/main.py) ----

class PendingPayment(BaseModel):
    """Money the shop still owes that is linked to a ticket. A human approves it; agents never pay."""

    kind: Literal["invoice", "rent"]
    ref_id: int = Field(description="The invoice id or the lease id to send to /api/approve.")
    amount: float
    payee: str
    due_date: str
    description: str


class TicketOut(BaseModel):
    """A ticket as the dashboard sees it."""

    id: int
    type: str
    requester: str
    subject: str
    status: str = Field(description="The ticket's real status: open, in_progress, waiting_on_approval or resolved.")
    state: Literal["open", "resolved"] = Field(description="Board view: resolved only when status is resolved.")
    sku: str | None = None
    size: str | None = None
    qty: int | None = None
    lease_id: int | None = None
    invoice_id: int | None = None
    notes: str | None = None
    created_at: str
    running: bool = Field(default=False, description="True while the agent team is working this ticket.")
    pending_payments: list[PendingPayment] = Field(
        default_factory=list, description="Linked bills or rent still unpaid. Approve these before closing the ticket."
    )
    has_draft_reply: bool = Field(default=False, description="An agent drafted a customer reply that a person should review.")
    can_close: bool = Field(
        default=False, description="The agents have prepared the ticket and nothing is left to pay: a person can close it now."
    )


class TicketsResponse(BaseModel):
    tickets: list[TicketOut]
    open: int
    resolved: int


class RunTicketResponse(BaseModel):
    run_id: str
    ticket: TicketOut
    result: TeamResult


class ToolUse(BaseModel):
    name: str
    args: str
    result: str


class EventOut(BaseModel):
    """One agent loop step, shaped for the board."""

    seq: int = Field(description="Position in the audit trail. Only grows, so it works as a cursor.")
    timestamp: str
    run_id: str
    ticket_id: int | None
    agent: str
    agent_run_id: str
    parent_agent_run_id: str | None
    iteration: int
    said: str | None = Field(description="What the agent said this step: its text, or the summary in its final report.")
    tools: list[ToolUse]
    guardrail_events: list[str]
    stop_reason: str
    approver: str | None


class EventsResponse(BaseModel):
    events: list[EventOut]
    total: int = Field(description="Entries in the whole audit trail.")
    latest_seq: int = Field(description="Highest seq in the trail (-1 if empty). Pass it back as since_seq to poll.")
    running_tickets: list[int]


class ApproveRequest(BaseModel):
    """A human clicked Approve."""

    kind: Literal["invoice", "rent"] = Field(description="invoice: pay a vendor bill (this is how a purchase is paid). rent: pay a lease.")
    ref_id: int = Field(description="The invoice id or the lease id.")
    approved_by: str = Field(description="The person who clicked approve.")
    ticket_id: int | None = Field(default=None, description="Ticket to note the payment on.")
    resolve_ticket: bool = Field(default=False, description="Mark that ticket resolved after the payment goes through.")


class ApproveResponse(BaseModel):
    ok: bool
    payment: dict[str, Any]
    checking_balance: float
    ticket: TicketOut | None = None


class CashResponse(BaseModel):
    account: str
    balance: float
    as_of: str


class ResetResponse(BaseModel):
    ok: bool
    restored_from: str
    open: int
    resolved: int
    checking_balance: float
    note: str


class ResolveRequest(BaseModel):
    """A human reviewed the agents' work (and any drafted reply) and closes the ticket."""

    approved_by: str
    note: str | None = Field(default=None, description="Optional extra words for the ticket note.")


class ResolveResponse(BaseModel):
    ok: bool
    ticket: TicketOut


class LiveEvent(BaseModel):
    """Something that happened right now in a run: the ticket went out, a specialist was sent, a specialist finished."""

    seq: int
    timestamp: str
    type: Literal["run_started", "dispatch", "agent_done", "run_finished"]
    ticket_id: int | None
    run_id: str
    agent: str
    task: str | None = None
    status: str | None = None


class LiveResponse(BaseModel):
    events: list[LiveEvent]
    latest_seq: int
    running_tickets: list[int]


class PaymentOut(BaseModel):
    """One row of the payments table, with who it went to and which ticket it belongs to."""

    id: int
    kind: str
    ref_id: int | None
    amount: float
    account: str
    paid_at: str
    approved_by: str
    payee: str | None
    description: str | None
    ticket_id: int | None


class PaymentsResponse(BaseModel):
    payments: list[PaymentOut]
    starting_balance: float = Field(description="Checking balance before the first payment (balance now plus everything paid).")
    checking_balance: float
