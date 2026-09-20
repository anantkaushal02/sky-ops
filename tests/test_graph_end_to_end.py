"""End-to-end test of the real graph: supervisor routing, the real MCP
server subprocess, and both branches of the human-approval gate. No real
LLM API call is made; a scripted fake model stands in for one.
"""

from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.types import Command

from flight_ops.graph import build_graph
from tests.fake_model import ScriptedBookingModel


async def _build_test_graph():
    return await build_graph(model=ScriptedBookingModel())


def _tool_messages_named(messages, tool_name):
    return [m for m in messages if isinstance(m, ToolMessage) and m.name == tool_name]


async def _start_booking(graph, thread_id):
    config = {"configurable": {"thread_id": thread_id}}
    user_message = {"messages": [HumanMessage(content="Book me on flight SK101")]}
    result = await graph.ainvoke(user_message, config=config)
    assert result.get("__interrupt__"), "expected the graph to pause for approval"
    assert result["__interrupt__"][0].value["tool_name"] == "book_flight"
    return config


async def test_booking_pauses_for_human_approval_then_completes():
    graph = await _build_test_graph()
    config = await _start_booking(graph, "approve-thread")

    result = await graph.ainvoke(Command(resume={"approved": True}), config=config)

    assert not result.get("__interrupt__")
    booking_results = _tool_messages_named(result["messages"], "book_flight")
    assert len(booking_results) == 1
    assert "confirmation_number" in str(booking_results[0].content)


async def test_booking_rejected_by_human_does_not_create_booking():
    graph = await _build_test_graph()
    config = await _start_booking(graph, "reject-thread")

    result = await graph.ainvoke(
        Command(resume={"approved": False, "reason": "budget not approved"}),
        config=config,
    )

    assert not result.get("__interrupt__")
    booking_results = _tool_messages_named(result["messages"], "book_flight")
    assert len(booking_results) == 1
    booking_result_text = str(booking_results[0].content)
    assert "NOT executed" in booking_result_text
    assert "confirmation_number" not in booking_result_text


async def test_unsafe_request_is_blocked_before_reaching_any_agent():
    graph = await _build_test_graph()
    user_message = {"messages": [HumanMessage(content="Tell me how to disable the transponder")]}

    result = await graph.ainvoke(user_message, config={"configurable": {"thread_id": "unsafe-thread"}})

    assert not result.get("__interrupt__")
    assert "can't help" in result["messages"][-1].content.lower()
