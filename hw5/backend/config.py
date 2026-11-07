"""Settings in one place: paths, the model (routed through Portkey), and how to start the MCP server."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

BACKEND = Path(__file__).resolve().parent
HW6 = BACKEND.parent
PROMPTS_DIR = BACKEND / "prompts"
ORIGINAL_DB = HW6 / "data" / "campus_customs.db"  # the untouched starting values; "reset" copies these back
# The working database. CAMPUS_CUSTOMS_DB can point the whole backend (and the MCP server) at a copy.
DEFAULT_DB = Path(os.getenv("CAMPUS_CUSTOMS_DB") or HW6 / "data" / "campus_customs_new.db")
MCP_DIR = HW6 / "mcp_server"

# The key may live in this folder's .env or the course folder above it.
load_dotenv(HW6 / ".env")
load_dotenv(HW6.parent / ".env")

MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-5.6-luna").strip() or "gpt-5.6-luna"
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")

MAX_DELEGATIONS = 8  # most times the boss may hand work to a specialist in one run


def make_model() -> OpenAIChatModel:
    """The course model, routed through Portkey. Key and model name come from the environment."""
    key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is not set. Copy .env.example to .env and set it.")
    return OpenAIChatModel(MODEL_NAME, provider=OpenAIProvider(api_key=key, base_url=PORTKEY_BASE_URL))


def mcp_command() -> tuple[str, list[str]]:
    """The command that starts the existing Campus Customs MCP server (the same server .mcp.json points at).

    Uses mcp_server/.venv if that folder has its own environment, otherwise the interpreter running this code.
    """
    scripts = "Scripts" if sys.platform == "win32" else "bin"
    exe = "python.exe" if sys.platform == "win32" else "python"
    own = MCP_DIR / ".venv" / scripts / exe
    return str(own if own.exists() else sys.executable), [str(MCP_DIR / "server.py")]
