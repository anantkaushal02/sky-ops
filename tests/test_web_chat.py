"""Exercises the WebSocket chat protocol end to end - real MCP server
subprocess, real supervisor routing, real HITL interrupt/resume - using the
scripted fake model so no LLM API call is made.
"""

from fastapi.testclient import TestClient

from flight_ops.scripted_model import ScriptedBookingModel
from flight_ops.web.app import create_app


def _client():
    app = create_app(model=ScriptedBookingModel(), daily_limit=100)
    return TestClient(app)


def test_booking_flow_pauses_for_approval_then_confirms():
    # The scripted model's own canned final text never mentions tool
    # results (see flight_ops.scripted_model) - that's covered against a
    # real ToolMessage in test_graph_end_to_end.py. This test's job is the
    # WebSocket transport: does an interrupt actually reach the client, and
    # does approving it resume the graph to a normal, non-interrupted reply.
    with _client() as client:
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "user_message", "text": "Book me on flight SK101"})
            approval = ws.receive_json()
            assert approval["type"] == "approval_request"
            assert approval["tool_name"] == "book_flight"

            ws.send_json({"type": "approval_response", "approved": True})
            reply = ws.receive_json()
            assert reply["type"] == "assistant_message"


def test_rejecting_the_approval_also_resumes_cleanly():
    with _client() as client:
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "user_message", "text": "Book me on flight SK101"})
            ws.receive_json()

            ws.send_json({"type": "approval_response", "approved": False, "reason": "not now"})
            reply = ws.receive_json()
            assert reply["type"] == "assistant_message"


def test_daily_limit_returns_a_friendly_error_instead_of_a_crash():
    app = create_app(model=ScriptedBookingModel(), daily_limit=0)
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"type": "user_message", "text": "hello"})
            reply = ws.receive_json()
            assert reply["type"] == "error"
