"""Connection from the agents to the existing Campus Customs MCP server, plus the guardrails
that run in code (not in a prompt) on every tool call the agents make."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from pydantic_ai import RunContext
from pydantic_ai.mcp import CallToolFunc, MCPToolset, ToolResult

from config import DEFAULT_DB, mcp_command
from models import TeamContext

PAYMENT_TOOLS = {"pay_invoice", "pay_rent"}


async def guard_tool_call(
    ctx: RunContext[TeamContext], call_tool: CallToolFunc, name: str, args: dict[str, Any]
) -> ToolResult:
    """Runs around every MCP tool call.

    - Payments: the model never chooses who approved. The approver is the person who started the
      run; with no approver the call is blocked before it reaches the server.
    - Ticket notes are always signed with the calling agent's own name.
    """
    deps = ctx.deps
    if name in PAYMENT_TOOLS:
        if not deps.approver:
            deps.guardrail_events.append(f"Blocked {name}: no human approver was given for this run.")
            return {
                "ok": False,
                "paid": False,
                "error": "Blocked: payments need a named human approver and none was given for this run. "
                "Report this as needing approval.",
            }
        args = {**args, "approved_by": deps.approver}
        deps.guardrail_events.append(f"{name}: approved_by set to '{deps.approver}' by the harness, not by the agent.")
    if name == "update_ticket":
        args = {**args, "updated_by": deps.agent}
        if args.get("status") == "resolved":  # only a person closes a ticket
            args["status"] = "waiting_on_approval"
            deps.guardrail_events.append("update_ticket: an agent tried to resolve the ticket; set to waiting_on_approval instead.")
    return await call_tool(name, args)


def make_toolset(db_path: Path | None = None) -> MCPToolset:
    """One shared connection to the MCP server (started over stdio) for the whole team run."""
    command, args = mcp_command()
    env = {"CAMPUS_CUSTOMS_DB": str(db_path or DEFAULT_DB)}
    client = Client(StdioTransport(command=command, args=args, env=env))
    return MCPToolset(client, process_tool_call=guard_tool_call)


async def call_mcp_tool(name: str, args: dict[str, Any], db_path: Path | None = None) -> dict[str, Any]:
    """Call one MCP tool directly (no agent in between) and return its result as a dict.

    Used by the back end for the human-approved actions, so they go through the same server
    and the same checks as everything else.
    """
    command, server_args = mcp_command()
    env = {"CAMPUS_CUSTOMS_DB": str(db_path or DEFAULT_DB)}
    async with Client(StdioTransport(command=command, args=server_args, env=env)) as client:
        res = await client.call_tool(name, args, raise_on_error=False)
        if res.data is not None:
            return res.data
        return json.loads(res.content[0].text)
