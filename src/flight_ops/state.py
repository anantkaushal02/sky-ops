"""Shared graph state schema for the top-level SkyOps Copilot graph."""

from typing import Optional

from langgraph.graph import MessagesState


class CopilotState(MessagesState):
    """Conversation state, extended with guardrail bookkeeping.

    `messages` is inherited from MessagesState and is the only field the
    supervisor and specialist agent subgraphs read or write. The guardrail
    fields below are only read/written by the input and output guardrail
    nodes in graph.py.
    """

    blocked: bool
    block_reason: Optional[str]
