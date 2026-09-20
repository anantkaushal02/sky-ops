"""Environment and model configuration for SkyOps Copilot."""

import os

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.language_models.chat_models import BaseChatModel

load_dotenv()

DEFAULT_MODEL = "anthropic:claude-sonnet-5"
MCP_SERVER_MODULE = "flight_ops.mcp.server"

# init_chat_model's provider prefix doesn't always match the provider SDK's
# env var name (e.g. "google_genai" reads GOOGLE_API_KEY, not
# GOOGLE_GENAI_API_KEY). Only exceptions to the "<PROVIDER>_API_KEY" default
# need an entry here.
API_KEY_ENV_VAR_OVERRIDES = {
    "google_genai": "GOOGLE_API_KEY",
}


def get_chat_model() -> BaseChatModel:
    """Build the chat model used by the supervisor and every specialist agent.

    The model is selected via the FLIGHT_OPS_MODEL env var, e.g.
    "anthropic:claude-sonnet-5", "openai:gpt-4o-mini", or
    "google_genai:gemini-2.5-flash". The matching provider API key must be
    set (ANTHROPIC_API_KEY / OPENAI_API_KEY / GOOGLE_API_KEY).
    """
    model_name = os.environ.get("FLIGHT_OPS_MODEL", DEFAULT_MODEL)
    provider = model_name.split(":", 1)[0]
    api_key_env_var = API_KEY_ENV_VAR_OVERRIDES.get(provider, f"{provider.upper()}_API_KEY")
    if not os.environ.get(api_key_env_var):
        raise RuntimeError(
            f"{api_key_env_var} is not set. Copy .env.example to .env and "
            f"add your key, or change FLIGHT_OPS_MODEL to a provider you "
            f"have a key for."
        )
    return init_chat_model(model_name, temperature=0)
