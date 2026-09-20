"""Extract plain text from a LangChain message's content field.

Different providers shape `.content` differently: Anthropic/OpenAI usually
return a plain string, while Gemini returns a list of content blocks (a
dict with a "text" key holding the actual answer, plus provider-specific
metadata like signatures). Guardrails and anything displaying a reply to a
human need the plain text, not the raw block structure.
"""

from typing import Any


def extract_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content)
