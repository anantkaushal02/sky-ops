"""Deterministic, regex-based safety policies for the guardrail nodes.

Kept rule-based (not another LLM call) so guardrail behavior is
predictable, fast, testable without an API key, and cannot itself be
prompt-injected.
"""

import re

SENSITIVE_TOOL_NAMES = {"book_flight", "cancel_booking"}

PROMPT_INJECTION_PATTERNS = [
    re.compile(r"ignore (all|any|the) (previous|prior|above) instructions", re.I),
    re.compile(r"reveal (your|the) (system|hidden) prompt", re.I),
    re.compile(r"you are now (in )?(dan|jailbreak) mode", re.I),
    re.compile(r"disregard (your|all) (safety|guardrail)s?", re.I),
]

UNSAFE_REQUEST_PATTERNS = [
    re.compile(r"\bhijack\b", re.I),
    re.compile(r"\bbomb (threat|on board)\b", re.I),
    re.compile(r"disable (the )?transponder", re.I),
    re.compile(r"bypass (tsa|security screening)", re.I),
    re.compile(r"\bsabotage\b", re.I),
    re.compile(r"smuggle a (weapon|firearm|explosive)", re.I),
]

ABSOLUTE_SAFETY_CLAIM_PATTERNS = [
    re.compile(r"\b100% safe\b", re.I),
    re.compile(r"\bguaranteed(?:\s+to\s+be)?\s+safe\b", re.I),
    re.compile(r"\bdefinitely safe to fly\b", re.I),
    re.compile(r"\bno risk at all\b", re.I),
]

PII_PATTERNS = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "phone": re.compile(r"\b\+?\d[\d\-. ]{8,}\d\b"),
    "passport": re.compile(r"\b[A-Z]{1,2}\d{6,9}\b"),
}

CONFIRMATION_NUMBER_PATTERN = re.compile(r"\bCONF-\d{5}\b")

SAFETY_DISCLAIMER = (
    "Note: flight safety determinations are advisory only and should be "
    "confirmed with official aviation authorities and airline dispatch "
    "before acting on them."
)
