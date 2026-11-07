"""The four specialist agents. Each has its own prompt file and only the MCP tools it needs."""

from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.models import Model

from config import PROMPTS_DIR
from models import SPECIALISTS, AgentReport, TeamContext

# Which MCP tools each specialist may see. Anything not listed is hidden from that agent.
ALLOWED_TOOLS: dict[str, set[str]] = {
    "inventory": {"get_ticket", "get_stock", "check_order", "suggest_restock", "update_ticket"},
    "accounting": {"get_ticket", "list_invoices", "get_cash_position", "pay_invoice", "pay_rent", "update_ticket"},
    "facilities": {"get_ticket", "get_lease", "get_cash_position", "update_ticket"},
    "customer_service": {"get_ticket", "list_tickets", "get_stock", "check_order", "quote_price", "update_ticket"},
}

DESCRIPTIONS = {
    "inventory": "stock levels, whether an order can be filled, and what to reorder from which vendor",
    "accounting": "vendor invoices, cash, and paying bills or rent (payments only happen with a human approver)",
    "facilities": "the shop's lease, rent notices, and whether rent is due and affordable",
    "customer_service": "customer tickets: price quotes, discount requests, and drafting replies to customers",
}


def build_specialist(name: str, toolset: MCPToolset, model: Model) -> Agent[TeamContext, AgentReport]:
    allowed = ALLOWED_TOOLS[name]
    return Agent(
        model,
        name=name,
        deps_type=TeamContext,
        output_type=AgentReport,
        instructions=(PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8"),
        toolsets=[toolset.filtered(lambda ctx, tool, allowed=allowed: tool.name in allowed)],
        retries=2,
    )


def build_specialists(toolset: MCPToolset, model: Model) -> dict[str, Agent[TeamContext, AgentReport]]:
    return {name: build_specialist(name, toolset, model) for name in SPECIALISTS}
