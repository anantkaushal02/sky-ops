"""Wires the input guardrail, the supervisor, and the output guardrail into
one compiled, checkpointed graph.

    START -> input_guardrail -> [blocked?] -> output_guardrail -> END
                               -> supervisor -> output_guardrail -> END

The checkpointer is only set on this outer compile. Interrupts raised deep
inside a specialist agent's tool call (see hitl.py) still pause this whole
graph, because LangGraph propagates one checkpointer down through subgraphs
used as nodes.
"""

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from flight_ops.agents import build_specialist_agents, build_supervisor_graph, load_tools, make_mcp_client
from flight_ops.config import get_chat_model
from flight_ops.guardrails.input_guardrails import screen_user_message
from flight_ops.guardrails.output_guardrails import enforce_output_guardrails
from flight_ops.state import CopilotState
from flight_ops.text_utils import extract_text


def _latest_human_text(messages: list) -> str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return str(message.content)
    return ""


def input_guardrail_node(state: CopilotState) -> dict:
    user_text = _latest_human_text(state["messages"])
    result = screen_user_message(user_text)
    if not result.blocked:
        return {"blocked": False, "block_reason": None}
    refusal = AIMessage(content=f"I can't help with that. {result.reason}")
    return {"blocked": True, "block_reason": result.reason, "messages": [refusal]}


def route_after_input_guardrail(state: CopilotState) -> str:
    return "blocked" if state.get("blocked") else "proceed"


def output_guardrail_node(state: CopilotState) -> dict:
    if state.get("blocked"):
        return {}
    last_message = state["messages"][-1]
    reply_text = extract_text(last_message.content)
    checked_text = enforce_output_guardrails(reply_text, state["messages"])
    if checked_text == last_message.content:
        return {}
    return {"messages": [AIMessage(content=checked_text, id=last_message.id)]}


async def build_graph(model=None):
    """Build and compile the full SkyOps Copilot graph. Returns the compiled graph.

    `model` can be overridden (e.g. with a scripted fake) for offline tests;
    production code should leave it as None to use the configured provider.
    """
    model = model or get_chat_model()
    mcp_client = make_mcp_client()
    all_tools = await load_tools(mcp_client)
    specialist_agents = build_specialist_agents(model, all_tools)
    supervisor = build_supervisor_graph(model, specialist_agents).compile()

    builder = StateGraph(CopilotState)
    builder.add_node("input_guardrail", input_guardrail_node)
    builder.add_node("supervisor", supervisor)
    builder.add_node("output_guardrail", output_guardrail_node)

    builder.add_edge(START, "input_guardrail")
    builder.add_conditional_edges(
        "input_guardrail",
        route_after_input_guardrail,
        {"proceed": "supervisor", "blocked": "output_guardrail"},
    )
    builder.add_edge("supervisor", "output_guardrail")
    builder.add_edge("output_guardrail", END)

    return builder.compile(checkpointer=InMemorySaver())
