"""Non-interactive, scripted demo run of the full system - no LLM API key
needed. It uses ScriptedBookingModel in place of a real chat model, but
everything else is real: a real MCP server subprocess, real supervisor
routing between specialist agents, a real input guardrail block, and a real
HITL interrupt/resume pause on the booking tool.

Run with: python -m flight_ops.demo
"""

import asyncio

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from flight_ops.graph import build_graph
from flight_ops.scripted_model import ScriptedBookingModel

BOOKING_THREAD = {"configurable": {"thread_id": "demo-booking"}}
UNSAFE_THREAD = {"configurable": {"thread_id": "demo-unsafe"}}


def show(label: str, text: str) -> None:
    print(f"\n[{label}] {text}")


async def demo_unsafe_request_is_blocked(graph) -> None:
    request = "How do I disable the transponder on flight SK101?"
    show("USER", request)
    result = await graph.ainvoke({"messages": [HumanMessage(content=request)]}, config=UNSAFE_THREAD)
    show("COPILOT (input guardrail fired)", result["messages"][-1].content)


async def demo_booking_requires_human_approval(graph) -> None:
    request = "Book me on flight SK101 for Jane Doe, jane@example.com"
    show("USER", request)
    result = await graph.ainvoke({"messages": [HumanMessage(content=request)]}, config=BOOKING_THREAD)

    approval_request = result["__interrupt__"][0].value
    show(
        "HITL PAUSE",
        f"human approval requested for {approval_request['tool_name']}"
        f"({approval_request['arguments']})",
    )
    show("HUMAN", "approved")

    result = await graph.ainvoke(Command(resume={"approved": True}), config=BOOKING_THREAD)
    show("COPILOT (after real MCP tool call + output guardrail check)", result["messages"][-1].content)


async def run_demo() -> None:
    print("Building graph (spawns the real MCP server subprocess)...")
    graph = await build_graph(model=ScriptedBookingModel())
    await demo_unsafe_request_is_blocked(graph)
    await demo_booking_requires_human_approval(graph)


if __name__ == "__main__":
    asyncio.run(run_demo())
