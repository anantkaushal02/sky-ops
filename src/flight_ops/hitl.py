"""Human-in-the-loop gate for sensitive tool calls.

Wraps a tool so that calling it pauses the graph with `interrupt()` and asks
a human to approve or reject the exact call before it runs for real. This
works no matter how deep the tool sits inside the supervisor -> specialist
agent -> tool-node call chain, because `interrupt()` pauses the whole graph
run, not just the current node.
"""

from langchain_core.tools import BaseTool, StructuredTool


def wrap_with_human_approval(tool: BaseTool) -> BaseTool:
    """Return a copy of `tool` that requires human approval before it runs."""
    from langgraph.types import interrupt

    async def gated_call(**arguments):
        decision = interrupt(
            {
                "kind": "tool_approval_request",
                "tool_name": tool.name,
                "tool_description": tool.description,
                "arguments": arguments,
            }
        )
        approved = decision.get("approved", False) if isinstance(decision, dict) else bool(decision)
        if not approved:
            reason = decision.get("reason", "not specified") if isinstance(decision, dict) else "not specified"
            return (
                f"Action '{tool.name}' was NOT executed: a human reviewer "
                f"rejected it. Reason: {reason}"
            )
        return await tool.ainvoke(arguments)

    return StructuredTool(
        name=tool.name,
        description=f"{tool.description} (requires human approval before executing)",
        args_schema=tool.args_schema,
        coroutine=gated_call,
    )
