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

## Tests

The test suite runs fully offline: no API key needed. It uses a small
scripted fake chat model (`tests/fake_model.py`) so the real MCP server, the
real supervisor routing, and the real HITL interrupt/resume flow are all
exercised without a live LLM call.

```bash
pip install -e ".[dev]"
pytest
```

## Project layout

```
src/flight_ops/
  config.py          # model selection from env vars
  state.py            # shared graph state schema
  agents.py           # builds the 4 specialist agents + the supervisor
  hitl.py              # wraps a tool so it requires human approval
  graph.py             # wires guardrails + supervisor into one compiled graph
  cli.py               # interactive terminal chat loop
  mcp/
    server.py          # the MCP tool server (FastMCP, stdio transport)
    data.py             # mock flights/weather/maintenance/bookings data
  guardrails/
    policies.py         # regex-based safety rules (single source of truth)
    input_guardrails.py  # screens the user's message
    output_guardrails.py # checks the assistant's reply
tests/
  fake_model.py         # scripted chat model for offline tests
  test_guardrails.py
  test_mcp_server.py
  test_graph_end_to_end.py
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
