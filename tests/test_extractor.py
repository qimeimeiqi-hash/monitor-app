import pytest

from src.extractor import ExtractionError, extract_text


def test_extract_text_returns_normalized_text_for_matching_selector():
    html = "<html><body><h1>  Hello   World  </h1></body></html>"

    result = extract_text(html, "h1")

    assert result == "Hello World"


def test_extract_text_raises_extraction_error_when_selector_not_found():
    html = "<html><body><p>content</p></body></html>"

    with pytest.raises(ExtractionError):
        extract_text(html, ".missing-class")


def test_extract_text_joins_multiple_matched_elements():
    html = "<html><body><li>one</li><li>two</li></body></html>"

    result = extract_text(html, "li")

    assert result == "one two"
