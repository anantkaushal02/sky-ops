"""A deterministic fake chat model so the full graph can be exercised in
tests without any real LLM API call.

It looks at which tools are currently bound (supervisor's handoff tools vs.
a specialist's real tools) and which tool names already appear in the
message history, then plays back one fixed step of a scripted plan at a
time. Once nothing is left to call, it returns a final text answer.
"""

from typing import Any, List, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class ScriptedBookingModel(BaseChatModel):
    bound_tools: List[Any] = []

    def bind_tools(self, tools, **kwargs):
        clone = self.model_copy()
        clone.bound_tools = list(tools)
        return clone

    @property
    def _llm_type(self) -> str:
        return "scripted-booking-model"

    @staticmethod
    def _called_tool_names(messages: List[BaseMessage]) -> set[str]:
        called = set()
        for message in messages:
            if isinstance(message, AIMessage):
                called.update(tool_call["name"] for tool_call in message.tool_calls)
        return called

    def _bound_tool_names(self) -> set[str]:
        return {tool.name for tool in self.bound_tools}

    def _next_ai_message(self, messages: List[BaseMessage]) -> AIMessage:
        bound_names = self._bound_tool_names()
        called_names = self._called_tool_names(messages)

        if "transfer_to_booking_agent" in bound_names and "transfer_to_booking_agent" not in called_names:
            return _tool_call_message("transfer_to_booking_agent", {})

        if "book_flight" in bound_names and "book_flight" not in called_names:
            args = {
                "flight_number": "SK101",
                "passenger_name": "Jane Doe",
                "passenger_email": "jane@example.com",
            }
            return _tool_call_message("book_flight", args)

        return AIMessage(content="Your request has been handled.")

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        ai_message = self._next_ai_message(messages)
        return ChatResult(generations=[ChatGeneration(message=ai_message)])


def _tool_call_message(name: str, args: dict) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": f"call_{name}"}])
