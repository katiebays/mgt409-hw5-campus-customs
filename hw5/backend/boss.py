"""The boss agent and the whole team run.

The boss reads the ticket queue and hands work to the four specialists through delegation
tools. Each handoff is a full agent loop of its own (model -> tools -> model ... -> report),
logged to the audit trail with the boss's agent_run_id as its parent. Specialists never talk
to each other directly: everything goes through the boss.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from pydantic_ai import Agent, RunContext, Tool

import live
from audit import run_with_audit
from config import DEFAULT_DB, MAX_DELEGATIONS, MODEL_NAME, PROMPTS_DIR, make_model
from mcp_client import make_toolset
from models import SPECIALISTS, TeamContext, TeamResult
from specialists import DESCRIPTIONS, build_specialists

BOSS_TOOLS = {"list_tickets", "get_ticket"}  # the boss only reads the queue; specialists make changes
MAX_TASK_CHARS = 1500


def _delegation_tool(name: str, team: dict[str, Agent]) -> Tool:
    async def delegate(ctx: RunContext[TeamContext], task: str) -> dict[str, Any]:
        boss = ctx.deps
        count = boss.shared["delegations"] = boss.shared.get("delegations", 0) + 1
        if count > MAX_DELEGATIONS:
            boss.guardrail_events.append(f"Blocked delegation #{count} to {name}: limit of {MAX_DELEGATIONS} per run.")
            return {"status": "blocked", "summary": f"Delegation limit of {MAX_DELEGATIONS} reached. Stop and report."}
        sub = TeamContext(
            run_id=boss.run_id,
            agent=name,  # type: ignore[arg-type]
            parent_agent_run_id=boss.agent_run_id,
            approver=boss.approver,
            database=boss.database,
            task=task[:MAX_TASK_CHARS],
            ticket_id=boss.ticket_id,
            shared=boss.shared,
        )
        live.emit("dispatch", ticket_id=boss.ticket_id, run_id=boss.run_id, agent=name, task=task)
        try:
            result = await run_with_audit(team[name], task[:MAX_TASK_CHARS], deps=sub, model_name=MODEL_NAME)
        except Exception as exc:  # the audit trail already has the error step
            live.emit("agent_done", ticket_id=boss.ticket_id, run_id=boss.run_id, agent=name, status="blocked")
            return {"status": "blocked", "summary": f"{name} could not finish: {type(exc).__name__}: {exc}"}
        live.emit("agent_done", ticket_id=boss.ticket_id, run_id=boss.run_id, agent=name, status=result.output.status)
        return result.output.model_dump()

    return Tool(
        delegate,
        name=f"ask_{name}",
        description=(
            f"Hand a task to the {name.replace('_', ' ')} agent, who handles {DESCRIPTIONS[name]}. "
            "Write the task so it stands alone: name the ticket ids and say exactly what you need back."
        ),
    )


async def run_team(
    message: str, *, approver: str | None = None, db_path: Path | None = None, ticket_id: int | None = None
) -> tuple[TeamResult, str]:
    """Run the boss (and through it the specialists) on one request. Returns the result and the run id.

    `ticket_id` is stamped on every audit entry so the dashboard can show one ticket's events.
    """
    db = Path(db_path) if db_path else DEFAULT_DB
    model = make_model()
    run_id = uuid.uuid4().hex[:12]
    toolset = make_toolset(db)
    specialists = build_specialists(toolset, model)
    boss = Agent(
        model,
        name="boss",
        deps_type=TeamContext,
        output_type=TeamResult,
        instructions=(PROMPTS_DIR / "boss.md").read_text(encoding="utf-8"),
        toolsets=[toolset.filtered(lambda ctx, tool: tool.name in BOSS_TOOLS)],
        tools=[_delegation_tool(n, specialists) for n in SPECIALISTS],
        retries=2,
    )
    deps = TeamContext(
        run_id=run_id, agent="boss", approver=approver, database=str(db), task=message,
        ticket_id=ticket_id, shared={"delegations": 0},
    )
    live.emit("run_started", ticket_id=ticket_id, run_id=run_id, agent="boss", task=message)
    try:
        async with toolset:  # one MCP connection shared by every agent in the run
            result = await run_with_audit(boss, message, deps=deps, model_name=MODEL_NAME)
    except Exception:
        live.emit("run_finished", ticket_id=ticket_id, run_id=run_id, agent="boss", status="error")
        raise
    live.emit("run_finished", ticket_id=ticket_id, run_id=run_id, agent="boss", status="done")
    return result.output, run_id
