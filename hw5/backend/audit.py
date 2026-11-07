"""Append-only audit trail: output/audit_trail.json.

Every step of every agent's loop adds one entry (who, what they were asked, the model's
text, each tool call with its arguments and result, rules the code enforced, tokens, and
why the step ended). The file is a JSON list. Entries are only added at the end: new text
is written over the closing bracket, so earlier entries are never rewritten and nothing wipes
the file between runs. If the file exists but is not a JSON list, we refuse to touch it.
"""

from __future__ import annotations

import json
import logging
import os
import re
import textwrap
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.messages import RetryPromptPart, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.usage import UsageLimits

from models import AuditEntry, AuditToolCall, TeamContext

log = logging.getLogger("campus.audit")

AUDIT_PATH = Path(os.environ.get("AUDIT_PATH", Path(__file__).resolve().parents[1] / "output" / "audit_trail.json"))
TOOL_CHARS = 600  # longest tool args / result text kept per call
TEXT_CHARS = 600
TASK_CHARS = 300
MAX_AGENT_STEPS = 12  # safety stop: most model requests one agent may make in a turn

_lock = threading.Lock()


def _short(value: Any, limit: int = TOOL_CHARS) -> str:
    if isinstance(value, BaseModel):
        text = value.model_dump_json()
    elif isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, default=str)
    else:
        text = str(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def append_audit(entry: AuditEntry) -> None:
    """Add one entry to the end of the audit file, keeping everything already in it."""
    block = textwrap.indent(json.dumps(entry.model_dump(), indent=2, ensure_ascii=False), "  ")
    with _lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not AUDIT_PATH.exists() or AUDIT_PATH.stat().st_size == 0:
            AUDIT_PATH.write_text("[\n" + block + "\n]\n", encoding="utf-8")
            return
        with AUDIT_PATH.open("r+b") as f:
            size = f.seek(0, os.SEEK_END)
            f.seek(max(0, size - 64))
            tail = f.read()
            body = tail.rstrip()
            if not body.endswith(b"]"):
                raise ValueError(f"{AUDIT_PATH.name} is not a JSON list; refusing to overwrite it.")
            body = body[:-1].rstrip()  # what comes before the closing bracket
            if not body.endswith((b"}", b"[")):
                raise ValueError(f"{AUDIT_PATH.name} is not a JSON list of entries; refusing to overwrite it.")
            keep = size - len(tail) + len(body)  # end of the last entry
            separator = b"\n" if body.endswith(b"[") else b",\n"
            f.truncate(keep)
            f.seek(keep)
            f.write(separator + block.encode("utf-8") + b"\n]\n")


def _safe_append(entry: AuditEntry) -> None:
    try:
        append_audit(entry)
    except Exception:  # an unwritable audit file must not stop the shop, but it must be noticed
        log.exception("Could not write the audit entry for run %s", entry.run_id)


async def run_with_audit(agent: Agent, prompt: str, *, deps: TeamContext, model_name: str):
    """Run one agent a loop step at a time, writing an audit entry as each step finishes.

    Returns the run result. `deps.agent`, `deps.agent_run_id`, `deps.parent_agent_run_id` and
    `deps.task` say whose turn this is.
    """
    if not deps.agent_run_id:
        deps.agent_run_id = uuid.uuid4().hex[:12]
    iteration = 0
    pending: AuditEntry | None = None
    calls_by_id: dict[str, AuditToolCall] = {}

    def new_entry(response=None, stop_reason: str = "") -> AuditEntry:
        return AuditEntry(
            run_id=deps.run_id,
            agent=deps.agent,
            agent_run_id=deps.agent_run_id,
            parent_agent_run_id=deps.parent_agent_run_id,
            iteration=iteration,
            timestamp="",
            task=_short(deps.task, TASK_CHARS),
            model=(response.model_name if response is not None else None) or model_name,
            database=deps.database,
            approver=deps.approver,
            ticket_id=deps.ticket_id,
            stop_reason=stop_reason,
            input_tokens=response.usage.input_tokens if response is not None else None,
            output_tokens=response.usage.output_tokens if response is not None else None,
        )

    def flush(stop_reason: str) -> None:
        nonlocal pending
        if pending is not None:
            pending.stop_reason = stop_reason
            pending.timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
            pending.guardrail_events = list(deps.guardrail_events)
            deps.guardrail_events.clear()
            _safe_append(pending)
            pending = None

    try:
        async with agent.iter(
            prompt, deps=deps, usage_limits=UsageLimits(request_limit=MAX_AGENT_STEPS)
        ) as run:
            async for node in run:
                if Agent.is_call_tools_node(node):
                    # The model answered: note what it said and which tools it wants to call.
                    response = node.model_response
                    iteration += 1
                    calls_by_id = {}
                    for part in response.parts:
                        if isinstance(part, ToolCallPart):
                            is_answer = part.tool_name.startswith("final_result")
                            calls_by_id[part.tool_call_id] = AuditToolCall(
                                tool_name=part.tool_name,
                                args=_short(part.args if isinstance(part.args, str) else json.dumps(part.args)),
                                result_summary="(final structured answer)" if is_answer else "(no result recorded)",
                            )
                    pending = new_entry(response)
                    text = " ".join(p.content for p in response.parts if isinstance(p, TextPart)).strip()
                    pending.assistant_text = _short(text, TEXT_CHARS) if text else None
                    pending.tool_calls = list(calls_by_id.values())
                elif Agent.is_model_request_node(node) and pending is not None:
                    # The tools have run: attach their results, then close this step.
                    for part in node.request.parts:
                        call = calls_by_id.get(getattr(part, "tool_call_id", ""))
                        if call is None:
                            continue
                        if isinstance(part, ToolReturnPart):
                            call.result_summary = _short(part.content)
                        elif isinstance(part, RetryPromptPart):
                            call.result_summary = "retry requested: " + _short(part.content)
                    flush("tool_call")
                elif Agent.is_end_node(node):
                    flush("final_result")
            return run.result
    except Exception as exc:
        if pending is None:
            iteration += 1
            pending = new_entry()
        flush(f"error: {type(exc).__name__}: {_short(exc, 200)}")
        raise


# ---- reading the trail back (for the dashboard) ----

def _said(entry: dict) -> str | None:
    """What the agent said this step: its own text, or the summary/answer inside its final report."""
    if entry.get("assistant_text"):
        return entry["assistant_text"]
    for call in entry.get("tool_calls", []):
        if str(call.get("tool_name", "")).startswith("final_result"):
            args = call.get("args", "")
            try:
                data = json.loads(args)
                return data.get("summary") or data.get("answer")
            except (ValueError, AttributeError):
                # The args were cut to 600 characters, so the JSON may be incomplete: pull the text out anyway.
                m = re.search(r'"(?:summary|answer)"\s*:\s*"((?:[^"\\]|\\.)*)', args)
                if m:
                    try:
                        return json.loads('"' + m.group(1) + '"')
                    except ValueError:
                        return m.group(1)
    return None


def read_events(
    limit: int = 50, ticket_id: int | None = None, run_id: str | None = None, since_seq: int | None = None
) -> tuple[list[dict], int]:
    """Recent entries from the audit trail, oldest first, each with `seq` (its position in the file).

    Returns (events, total entries in the trail). `since_seq` keeps only entries after that position.
    """
    if not AUDIT_PATH.exists() or AUDIT_PATH.stat().st_size == 0:
        return [], 0
    with _lock:
        entries = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    events = []
    for seq, e in enumerate(entries):
        if since_seq is not None and seq <= since_seq:
            continue
        if ticket_id is not None and e.get("ticket_id") != ticket_id:
            continue
        if run_id is not None and e.get("run_id") != run_id:
            continue
        events.append(
            {
                "seq": seq,
                "timestamp": e.get("timestamp", ""),
                "run_id": e.get("run_id", ""),
                "ticket_id": e.get("ticket_id"),
                "agent": e.get("agent", ""),
                "agent_run_id": e.get("agent_run_id", ""),
                "parent_agent_run_id": e.get("parent_agent_run_id"),
                "iteration": e.get("iteration", 0),
                "said": _said(e),
                "tools": [
                    {"name": c.get("tool_name", ""), "args": c.get("args", ""), "result": c.get("result_summary", "")}
                    for c in e.get("tool_calls", [])
                    if not str(c.get("tool_name", "")).startswith("final_result")
                ],
                "guardrail_events": e.get("guardrail_events", []),
                "stop_reason": e.get("stop_reason", ""),
                "approver": e.get("approver"),
            }
        )
    return events[-limit:], len(entries)


def log_human_approval(
    *, tool: str, args: dict, result: dict, approver: str, database: str, ticket_id: int | None
) -> None:
    """Record a human clicking Approve (the one place money moves) in the same audit trail."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _safe_append(
        AuditEntry(
            run_id="approval-" + uuid.uuid4().hex[:8],
            agent="human",
            agent_run_id=uuid.uuid4().hex[:12],
            parent_agent_run_id=None,
            iteration=1,
            timestamp=now,
            task=_short(f"Human approved {tool}", TASK_CHARS),
            model="n/a",
            database=database,
            approver=approver,
            ticket_id=ticket_id,
            tool_calls=[AuditToolCall(tool_name=tool, args=_short(json.dumps(args)), result_summary=_short(result))],
            stop_reason="final_result" if result.get("ok") else "refused",
        )
    )
