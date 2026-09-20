"""Interactive terminal chat loop for SkyOps Copilot, with HITL approval prompts."""

import asyncio

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from flight_ops.graph import build_graph

THREAD_CONFIG = {"configurable": {"thread_id": "skyops-cli-session"}}


def print_banner() -> None:
    print("=" * 60)
    print("SkyOps Copilot - flight operations multi-agent assistant")
    print("Type 'exit' to quit.")
    print("=" * 60)


def ask_human_approval(request: dict) -> dict:
    print("\n--- HUMAN APPROVAL REQUIRED ---")
    print(f"Tool: {request['tool_name']}")
    print(f"Description: {request['tool_description']}")
    print(f"Arguments: {request['arguments']}")
    answer = input("Approve this action? [y/N]: ").strip().lower()
    if answer == "y":
        return {"approved": True}
    reason = input("Reason for rejecting (optional): ").strip()
    return {"approved": False, "reason": reason or "not specified"}


async def run_turn(graph, resumable_input) -> None:
    result = await graph.ainvoke(resumable_input, config=THREAD_CONFIG)
    pending_interrupts = result.get("__interrupt__")
    while pending_interrupts:
        decision = ask_human_approval(pending_interrupts[0].value)
        result = await graph.ainvoke(Command(resume=decision), config=THREAD_CONFIG)
        pending_interrupts = result.get("__interrupt__")
    print(f"\nCopilot: {result['messages'][-1].content}")


async def main() -> None:
    print_banner()
    graph = await build_graph()
    while True:
        user_text = input("\nYou: ").strip()
        if user_text.lower() in {"exit", "quit"}:
            break
        if not user_text:
            continue
        await run_turn(graph, {"messages": [HumanMessage(content=user_text)]})


def main_sync() -> None:
    """Entry point for the `skyops` console script."""
    asyncio.run(main())


if __name__ == "__main__":
    main_sync()
