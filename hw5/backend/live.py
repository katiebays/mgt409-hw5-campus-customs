"""A small in-memory feed of what is happening during a run, for the dashboard's animation.

The audit trail records each agent step after it finishes. This feed records the moments
that need to show up instantly: the ticket going out, a specialist being sent a task, and a
specialist handing back its report. It is not an audit record and is lost on restart.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any

_lock = threading.Lock()
_events: list[dict[str, Any]] = []
_next = 0
KEEP = 500


def emit(type: str, *, ticket_id: int | None, run_id: str, agent: str, task: str | None = None, status: str | None = None) -> None:
    global _next
    with _lock:
        _events.append(
            {
                "seq": _next,
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                "type": type,
                "ticket_id": ticket_id,
                "run_id": run_id,
                "agent": agent,
                "task": (task or "")[:300] or None,
                "status": status,
            }
        )
        _next += 1
        del _events[:-KEEP]


def read(since_seq: int | None = None, ticket_id: int | None = None) -> tuple[list[dict[str, Any]], int]:
    """Events after `since_seq` (all if None), optionally for one ticket. Returns (events, latest seq or -1)."""
    with _lock:
        out = [
            e
            for e in _events
            if (since_seq is None or e["seq"] > since_seq) and (ticket_id is None or e["ticket_id"] == ticket_id)
        ]
        return out, _next - 1
