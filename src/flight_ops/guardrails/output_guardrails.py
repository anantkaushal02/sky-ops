"""Output guardrail: checks the assistant's final reply before it is shown.

Two independent checks:
1. Hedge unqualified safety guarantees with a disclaimer.
2. Catch hallucinated booking confirmation numbers by cross-checking every
   confirmation number mentioned in the reply against numbers that a real
   tool call actually returned earlier in the conversation.
"""

from langchain_core.messages import ToolMessage

from flight_ops.guardrails import policies
from flight_ops.text_utils import extract_text


def add_safety_disclaimer(reply_text: str) -> str:
    for pattern in policies.ABSOLUTE_SAFETY_CLAIM_PATTERNS:
        if pattern.search(reply_text):
            return f"{reply_text}\n\n{policies.SAFETY_DISCLAIMER}"
    return reply_text


def collect_real_confirmation_numbers(messages: list) -> set[str]:
    real_numbers: set[str] = set()
    for message in messages:
        if not isinstance(message, ToolMessage):
            continue
        content = extract_text(message.content)
        real_numbers.update(policies.CONFIRMATION_NUMBER_PATTERN.findall(content))
    return real_numbers


def flag_unverified_confirmation_numbers(reply_text: str, real_numbers: set[str]) -> str:
    mentioned_numbers = policies.CONFIRMATION_NUMBER_PATTERN.findall(reply_text)
    unverified_numbers = [n for n in mentioned_numbers if n not in real_numbers]
    if not unverified_numbers:
        return reply_text
    warning = (
        "\n\nWarning: this reply mentioned a booking confirmation number "
        f"({', '.join(unverified_numbers)}) that no tool call actually "
        "returned in this conversation. Treat it as unverified."
    )
    return f"{reply_text}{warning}"


def enforce_output_guardrails(reply_text: str, messages: list) -> str:
    checked_text = add_safety_disclaimer(reply_text)
    real_numbers = collect_real_confirmation_numbers(messages)
    checked_text = flag_unverified_confirmation_numbers(checked_text, real_numbers)
    return checked_text
