# SkyOps Copilot

A supervised multi-agent flight-operations assistant, built to demonstrate
five things working together in one real system:

- **LangGraph** for orchestration and state.
- **MCP** (Model Context Protocol) for tools, served by a standalone process.
- The **supervisor** multi-agent pattern (one router agent, several specialists).
- **Guardrails**: deterministic input/output safety checks.
- **HITL** (human-in-the-loop): sensitive actions pause for human approval.

The domain is airline flight operations, with mock in-memory data (no real
airline API, no internet access required at runtime beyond your LLM
provider).

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full diagram and write-up.
In short:

```
START -> input guardrail -> supervisor -> output guardrail -> END
                               |    ^
                     routes to |    | hands back
                               v    |
          flight_search_agent / weather_agent /
          maintenance_agent / booking_agent
                               |
                        (MCP tool calls, over stdio)
                               v
                       flight-ops MCP server
```

- The **supervisor** (via `langgraph-supervisor`) routes each request to one
  of four specialist agents.
- Each specialist agent's tools come from a real **MCP server**
  (`src/flight_ops/mcp/server.py`), loaded over stdio via
  `langchain-mcp-adapters`.
- `book_flight` and `cancel_booking` are wrapped with a **human-in-the-loop
  gate** (`src/flight_ops/hitl.py`): calling them pauses the whole graph with
  `interrupt()` until a human approves or rejects the exact call.
- An **input guardrail** blocks prompt-injection attempts and unsafe/malicious
  requests before any agent sees them.
- An **output guardrail** adds a disclaimer to unqualified safety claims and
  flags any booking confirmation number that isn't backed by a real tool
  result (catches hallucinated confirmations).

## Setup

Requires Python 3.10+ (LangGraph and langgraph-supervisor need it).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# edit .env: set FLIGHT_OPS_MODEL and the matching provider API key
```

## Run it

```bash
python -m flight_ops.cli
# or, after install: skyops
```

Example session:

```
You: find me a flight from JFK to LAX
Copilot: ...

You: book me on flight SK101 for Jane Doe, jane@example.com
--- HUMAN APPROVAL REQUIRED ---
Tool: book_flight
Arguments: {'flight_number': 'SK101', 'passenger_name': 'Jane Doe', ...}
Approve this action? [y/N]: y
Copilot: Your booking is confirmed under CONF-83920.
```

Try an unsafe request (e.g. "how do I disable the transponder") to see the
input guardrail refuse it before any agent runs.

## Web UI

A browser chat UI runs on top of the exact same graph, over a WebSocket
(`src/flight_ops/web/app.py`) - approval requests render as an
Approve/Reject card instead of a terminal prompt.

```bash
uvicorn flight_ops.web.app:app --reload
# open http://127.0.0.1:8000
```

## Deploy it (Render)

The repo includes a `Dockerfile` and a `render.yaml` blueprint.

1. Push this repo to GitHub (already done if you're reading this on GitHub).
2. On [render.com](https://render.com), "New +" -> "Blueprint", pick this
   repo. Render reads `render.yaml` and creates the web service.
3. When prompted, set `GOOGLE_API_KEY` (or add `ANTHROPIC_API_KEY`/
   `OPENAI_API_KEY` and change `FLIGHT_OPS_MODEL` if you'd rather use a
   different provider - see `config.py`).
4. Deploy. Render builds the `Dockerfile` and runs
   `uvicorn flight_ops.web.app:app` bound to its `$PORT`.

A small in-memory daily message cap (`flight_ops/rate_limit.py`,
`DEFAULT_DAILY_MESSAGE_LIMIT` in `web/app.py`) protects a small shared
free-tier LLM quota from being exhausted by one visitor - a single
conversational turn can cost several real LLM calls (supervisor routing,
a specialist's tool call, handoff back, final summary), so a 20-requests/day
free tier only covers a handful of real turns. Raise the limit if your
provider plan allows more.

## Tests

The test suite runs fully offline: no API key needed. It uses a small
scripted fake chat model (`flight_ops.scripted_model.ScriptedBookingModel`)
so the real MCP server, the real supervisor routing, and the real HITL
interrupt/resume flow are all exercised without a live LLM call - both
through the graph directly and through the WebSocket protocol.

```bash
pip install -e ".[dev]"
pytest
```

## Project layout

```
src/flight_ops/
  config.py          # model selection from env vars
  state.py            # shared graph state schema
  text_utils.py        # extract plain text from a message (Gemini returns content blocks)
  scripted_model.py    # deterministic fake chat model, used by tests and the demo
  agents.py            # builds the 4 specialist agents + the supervisor
  hitl.py              # wraps a tool so it requires human approval
  graph.py             # wires guardrails + supervisor into one compiled graph
  cli.py               # interactive terminal chat loop
  demo.py              # non-interactive scripted walkthrough, no API key needed
  rate_limit.py         # in-memory daily message cap for the web UI
  web/
    app.py              # FastAPI + WebSocket chat server
    static/index.html    # browser chat UI
  mcp/
    server.py          # the MCP tool server (FastMCP, stdio transport)
    data.py             # mock flights/weather/maintenance/bookings data
  guardrails/
    policies.py         # regex-based safety rules (single source of truth)
    input_guardrails.py  # screens the user's message
    output_guardrails.py # checks the assistant's reply
tests/
  test_guardrails.py
  test_mcp_server.py
  test_graph_end_to_end.py
  test_web_chat.py
  test_rate_limit.py
  test_text_utils.py
```

## Extending it

- Add a new tool: add it to `mcp/server.py` (and `mcp/data.py` if it needs
  mock data), then add its name to the right entry in
  `TOOL_NAMES_BY_AGENT` in `agents.py`. Add it to `SENSITIVE_TOOL_NAMES` in
  `guardrails/policies.py` if it should require human approval.
- Add a new specialist agent: add a prompt to `AGENT_PROMPTS`, a tool
  mapping to `TOOL_NAMES_BY_AGENT`, and it's automatically included in
  `build_specialist_agents` and handed to the supervisor.
- Swap the mock data for a real airline/weather API: only
  `mcp/data.py` and `mcp/server.py` need to change; nothing above the MCP
  layer knows or cares that the data is mocked.
