# Architecture

## Why a separate MCP server process

The tools (`search_flights`, `get_weather_briefing`, `book_flight`, ...) are
served by `src/flight_ops/mcp/server.py`, a standalone MCP server run over
stdio. The agent code (`agents.py`) never imports that server's internals -
it only talks to it through `langchain-mcp-adapters`'
`MultiServerMCPClient`, exactly as it would talk to a third-party MCP server.
This is the actual point of MCP: the tool implementation and the agent that
uses it are decoupled processes speaking a common protocol. You could
replace `mcp/server.py` with a real airline's MCP server and nothing in
`agents.py`, `graph.py`, or the guardrails would need to change.

## Why a supervisor instead of one big agent

One agent with 6 tools bound at once tends to pick the wrong tool for
ambiguous requests and makes the system harder to reason about (which tool
should ever run without approval?). Splitting by concern -
`flight_search_agent`, `weather_agent`, `maintenance_agent`,
`booking_agent` - keeps each agent's tool set small and its prompt focused,
and makes the sensitive/non-sensitive boundary line up exactly with
`booking_agent`. `langgraph-supervisor`'s `create_supervisor` builds the
router: it hands the supervisor model a "transfer_to_<agent>" tool per
specialist, and routes control there.

`create_supervisor` defaults to `output_mode="last_message"`, which hides
each worker's internal tool-call/tool-response messages from the shared
thread. This repo sets `output_mode="full_history"` instead
(`agents.py::build_supervisor_graph`) so that the real tool calls and their
results stay visible in the top-level conversation. Two things depend on
that: the output guardrail's confirmation-number check (it scans
`ToolMessage`s for the real value), and, in general, being able to audit
what actually happened.

## How the human-in-the-loop gate works

`hitl.py::wrap_with_human_approval` wraps a tool so that calling it does
this instead of running immediately:

1. Call `interrupt({"tool_name": ..., "arguments": ...})`. This raises a
   `GraphInterrupt` that propagates up through the tool node, the specialist
   agent's subgraph, and the supervisor's subgraph, pausing the *entire*
   compiled graph and persisting its state via the checkpointer
   (`InMemorySaver`, set only on the outermost `.compile()` call in
   `graph.py`).
2. The caller (the CLI, or a test) sees `result["__interrupt__"]`, shows the
   pending action to a human, and resumes the graph with
   `Command(resume={"approved": True/False, ...})`.
3. Execution resumes exactly where it paused. `interrupt()` returns the
   resume value. If approved, the wrapper calls the real tool
   (`tool.ainvoke(arguments)`); if not, it returns a message saying the
   action was rejected, and the real tool never runs.

Because subgraphs used as nodes automatically share the parent's
checkpointer when they don't set their own, this works without any special
plumbing in the specialist agents themselves - `create_react_agent` is
called with `checkpointer=None` for every specialist and for the
supervisor; only the top-level graph gets `checkpointer=InMemorySaver()`.

Only `book_flight` and `cancel_booking` are wrapped (see
`SENSITIVE_TOOL_NAMES` in `guardrails/policies.py`) - read-only tools like
`search_flights` run immediately.

## Guardrails: why deterministic, not another LLM call

Both guardrail layers (`guardrails/input_guardrails.py`,
`guardrails/output_guardrails.py`) are plain regex/set-membership checks
over `guardrails/policies.py`, not a second LLM call asking "is this safe?".
Three reasons:

- **Predictable**: the same input always gets the same guardrail decision,
  which matters for testing and for reasoning about what the system will
  and won't do.
- **Not itself promptable**: an LLM-based guardrail can in principle be
  talked out of its judgment by the same kind of injection it's supposed to
  catch. A regex match cannot.
- **Testable without an API key**: `tests/test_guardrails.py` runs in
  milliseconds with no network access.

The tradeoff is coverage: regexes catch known patterns, not every possible
phrasing of an unsafe request. For a production system, treat this layer as
a fast, cheap first line of defense, and pair it with an LLM-based or
human-reviewed second layer for anything the fast layer doesn't confidently
allow or block.

## The two guardrail checks in detail

**Input** (`input_guardrails.screen_user_message`): blocks the turn before
any agent or tool runs if the message matches a prompt-injection pattern
("ignore previous instructions", ...) or an unsafe-request pattern
("disable the transponder", "bomb threat", ...). `redact_pii` is available
separately for redacting emails/phones/passport-shaped strings before
writing anything to a log or audit trail - it is not applied to the text an
agent actually acts on, since a booking genuinely needs a real email
address.

**Output** (`output_guardrails.enforce_output_guardrails`), applied to the
final reply after the supervisor answers:

1. `add_safety_disclaimer` - if the reply contains an unqualified safety
   claim ("100% safe", "guaranteed safe", ...), append a disclaimer instead
   of blocking the reply outright.
2. `flag_unverified_confirmation_numbers` - collect every `CONF-#####`-shaped
   string that actually appears in a `ToolMessage` in this conversation
   (i.e., a real tool really returned it), then flag any confirmation
   number in the reply that isn't in that set. This is the check that
   catches a hallucinated "your booking is confirmed under CONF-00000" that
   no tool call ever produced.

## Testing without a live LLM

`tests/fake_model.py` implements `ScriptedBookingModel`, a minimal
`BaseChatModel` that inspects which tools are currently bound (the
supervisor's handoff tools vs. a specialist's real tools) and which tool
names already appear in the message history, then emits the next scripted
tool call or a final text answer. This is enough to drive the real graph -
real MCP server subprocess, real supervisor routing, real `interrupt()`/
`Command(resume=...)` flow - end to end with zero API calls and zero cost.
See `tests/test_graph_end_to_end.py`.
