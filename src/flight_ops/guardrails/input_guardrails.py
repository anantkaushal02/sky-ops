"""Input guardrail: screens the user's message before any agent sees it."""

from dataclasses import dataclass
from typing import Optional

from flight_ops.guardrails import policies


@dataclass
class InputScreenResult:
    blocked: bool
    reason: Optional[str]


def screen_user_message(message_text: str) -> InputScreenResult:
    """Block prompt-injection attempts and unsafe/malicious aviation requests."""
    for pattern in policies.PROMPT_INJECTION_PATTERNS:
        if pattern.search(message_text):
            return InputScreenResult(
                blocked=True,
                reason="This looks like an attempt to override the assistant's "
                "instructions, which isn't allowed.",
            )

    for pattern in policies.UNSAFE_REQUEST_PATTERNS:
        if pattern.search(message_text):
            return InputScreenResult(
                blocked=True,
                reason="This request involves an unsafe or malicious aviation "
                "action and can't be helped with.",
            )

    return InputScreenResult(blocked=False, reason=None)


def redact_pii(text: str) -> str:
    """Replace PII substrings with a labeled placeholder, for logs/audit trails only."""
    redacted_text = text
    for label, pattern in policies.PII_PATTERNS.items():
        redacted_text = pattern.sub(f"[REDACTED_{label.upper()}]", redacted_text)
    return redacted_text
