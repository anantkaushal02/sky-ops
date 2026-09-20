"""Builds the specialist agents and the supervisor that routes between them."""

import sys

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor

from flight_ops.guardrails.policies import SENSITIVE_TOOL_NAMES
from flight_ops.hitl import wrap_with_human_approval

TOOL_NAMES_BY_AGENT = {
    "flight_search_agent": {"search_flights", "get_flight_status"},
    "weather_agent": {"get_weather_briefing"},
    "maintenance_agent": {"get_aircraft_maintenance_status"},
    "booking_agent": {"book_flight", "cancel_booking"},
}


def make_mcp_client() -> MultiServerMCPClient:
    return MultiServerMCPClient(
        {
            "flight-ops": {
                "transport": "stdio",
                "command": sys.executable,
                "args": ["-m", "flight_ops.mcp.server"],
            }
        }
    )


async def load_tools(client: MultiServerMCPClient) -> list[BaseTool]:
    tools = await client.get_tools()
    gated_tools = []
    for tool in tools:
        if tool.name in SENSITIVE_TOOL_NAMES:
            gated_tools.append(wrap_with_human_approval(tool))
        else:
            gated_tools.append(tool)
    return gated_tools


def tools_for_agent(agent_name: str, all_tools: list[BaseTool]) -> list[BaseTool]:
    wanted_names = TOOL_NAMES_BY_AGENT[agent_name]
    return [tool for tool in all_tools if tool.name in wanted_names]


def build_specialist_agents(model: BaseChatModel, all_tools: list[BaseTool]) -> list:
    agents = []
    for agent_name, prompt in AGENT_PROMPTS.items():
        agent = create_react_agent(
            model=model,
            tools=tools_for_agent(agent_name, all_tools),
            prompt=prompt,
            name=agent_name,
        )
        agents.append(agent)
    return agents


AGENT_PROMPTS = {
    "flight_search_agent": (
        "You search for flights and report flight status. Use your tools to "
        "look up real data; never invent flight numbers, times, or prices."
    ),
    "weather_agent": (
        "You report airport weather briefings. Use your tools for real data. "
        "Never state a definitive safety guarantee about flying conditions."
    ),
    "maintenance_agent": (
        "You report aircraft maintenance and airworthiness status using your "
        "tools. Never state a definitive safety guarantee."
    ),
    "booking_agent": (
        "You book and cancel flight reservations using your tools. Every "
        "booking or cancellation requires human approval, which happens "
        "automatically when you call the tool - just call it normally."
    ),
}

SUPERVISOR_PROMPT = (
    "You are the SkyOps Copilot supervisor. Route the user's request to the "
    "one specialist agent best suited to it: flight_search_agent for "
    "searching flights or checking flight status, weather_agent for weather "
    "briefings, maintenance_agent for aircraft airworthiness, and "
    "booking_agent for booking or cancelling a reservation. Summarize the "
    "specialist's findings back to the user in plain language."
)


def build_supervisor_graph(model: BaseChatModel, specialist_agents: list):
    return create_supervisor(
        specialist_agents,
        model=model,
        prompt=SUPERVISOR_PROMPT,
        supervisor_name="supervisor",
        # Keep each worker's tool calls and tool results visible in the
        # shared thread (default "last_message" hides them), so the output
        # guardrail can verify real confirmation numbers and a human can
        # audit exactly what happened.
        output_mode="full_history",
    )
