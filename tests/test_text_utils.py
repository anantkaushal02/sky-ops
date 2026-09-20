from flight_ops.text_utils import extract_text


def test_extract_text_passes_through_plain_string():
    assert extract_text("hello") == "hello"


def test_extract_text_joins_gemini_style_content_blocks():
    content = [{"type": "text", "text": "hello", "extras": {"signature": "abc"}}]
    assert extract_text(content) == "hello"


def test_extract_text_handles_plain_string_blocks():
    assert extract_text(["hello", "world"]) == "helloworld"
