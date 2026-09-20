"""Environment and model configuration for SkyOps Copilot."""

import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

load_dotenv()

DEFAULT_MODEL = "anthropic:claude-sonnet-5"
MCP_SERVER_MODULE = "flight_ops.mcp.server"


def get_chat_model() -> BaseChatModel:
    """Build the chat model used by the supervisor and every specialist agent.

    The model is selected via the FLIGHT_OPS_MODEL env var, e.g.
    "anthropic:claude-sonnet-5" or "openai:gpt-4o-mini". The matching
    provider API key (ANTHROPIC_API_KEY / OPENAI_API_KEY) must be set.
    """
    model_name = os.environ.get("FLIGHT_OPS_MODEL", DEFAULT_MODEL)
    provider = model_name.split(":", 1)[0]
    api_key_env_var = f"{provider.upper()}_API_KEY"
    if not os.environ.get(api_key_env_var):
        raise RuntimeError(
            f"{api_key_env_var} is not set. Copy .env.example to .env and "
            f"add your key, or change FLIGHT_OPS_MODEL to a provider you "
            f"have a key for."
        )
    return init_chat_model(model_name, temperature=0)
