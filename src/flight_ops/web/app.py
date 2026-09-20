"""Browser front end for SkyOps Copilot.

Replaces the CLI's terminal input()/print() with a WebSocket protocol so
the same compiled graph (flight_ops.graph.build_graph) can run behind a
web server. Message shapes, client -> server:

    {"type": "user_message", "text": "..."}
    {"type": "approval_response", "approved": true/false, "reason": "..."}

Server -> client:

    {"type": "assistant_message", "text": "..."}
    {"type": "approval_request", "tool_name": "...", "tool_description": "...", "arguments": {...}}
    {"type": "error", "message": "..."}

Each WebSocket connection gets its own thread_id, so each browser tab is
an independent conversation.
"""

import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from flight_ops.graph import build_graph
from flight_ops.rate_limit import DailyMessageLimiter

STATIC_DIR = Path(__file__).parent / "static"

# Keeps headroom under a small shared free-tier LLM quota (e.g. Gemini's
# 20 requests/day): a single conversational turn can cost several real LLM
# calls (supervisor routing, specialist tool-call, handoff back, summary).
DEFAULT_DAILY_MESSAGE_LIMIT = 15

QUOTA_ERROR_MARKERS = ("RESOURCE_EXHAUSTED", "429", "rate limit")


def friendly_error(exc: Exception) -> str:
    if any(marker in str(exc) for marker in QUOTA_ERROR_MARKERS):
        return "The shared API quota is exhausted right now. Please try again later."
    return "Something went wrong handling that request. Please try again."


def create_app(model=None, daily_limit: int = DEFAULT_DAILY_MESSAGE_LIMIT) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.graph = await build_graph(model=model)
        app.state.limiter = DailyMessageLimiter(daily_limit)
        yield

    app = FastAPI(lifespan=lifespan)

    @app.get("/")
    async def index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.websocket("/ws")
    async def chat_socket(websocket: WebSocket):
        await handle_chat_connection(websocket, app.state.graph, app.state.limiter)

    return app


async def handle_chat_connection(websocket: WebSocket, graph, limiter: DailyMessageLimiter) -> None:
    await websocket.accept()
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    try:
        while True:
            message = await websocket.receive_json()
            if message.get("type") != "user_message":
                continue
            if not limiter.try_consume():
                await websocket.send_json({"type": "error", "message": DAILY_LIMIT_MESSAGE})
                continue
            await run_turn_and_reply(websocket, graph, config, message.get("text", ""))
    except WebSocketDisconnect:
        pass


DAILY_LIMIT_MESSAGE = (
    "This demo has hit its daily message limit (a shared free-tier API "
    "quota). Please try again after it resets."
)


async def run_turn_and_reply(websocket: WebSocket, graph, config: dict, text: str) -> None:
    try:
        result = await graph.ainvoke({"messages": [HumanMessage(content=text)]}, config=config)
        result = await resolve_pending_approvals(websocket, graph, config, result)
    except WebSocketDisconnect:
        raise
    except Exception as exc:
        await websocket.send_json({"type": "error", "message": friendly_error(exc)})
        return
    if result is not None:
        await websocket.send_json({"type": "assistant_message", "text": result["messages"][-1].content})


async def resolve_pending_approvals(websocket: WebSocket, graph, config: dict, result: dict):
    while result.get("__interrupt__"):
        approval_request = result["__interrupt__"][0].value
        await websocket.send_json({"type": "approval_request", **approval_request})
        decision_message = await websocket.receive_json()
        decision = {
            "approved": bool(decision_message.get("approved")),
            "reason": decision_message.get("reason", "not specified"),
        }
        result = await graph.ainvoke(Command(resume=decision), config=config)
    return result


app = create_app()
