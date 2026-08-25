from unittest.mock import Mock, patch

import pytest
import requests

from src.fetcher import FetchError, fetch_html


def test_fetch_html_returns_response_text_on_success():
    mock_response = Mock(status_code=200, text="<html>ok</html>")

    with patch("src.fetcher.requests.get", return_value=mock_response) as mock_get:
        result = fetch_html("https://example.com", timeout_seconds=5)

    assert result == "<html>ok</html>"
    mock_get.assert_called_once_with("https://example.com", timeout=5)


def test_fetch_html_raises_fetch_error_on_non_200_status():
    mock_response = Mock(status_code=404, text="not found")

    with patch("src.fetcher.requests.get", return_value=mock_response):
        with pytest.raises(FetchError):
            fetch_html("https://example.com/missing")


def test_fetch_html_raises_fetch_error_on_request_timeout():
    with patch("src.fetcher.requests.get", side_effect=requests.exceptions.Timeout("timed out")):
        with pytest.raises(FetchError):
            fetch_html("https://example.com/slow")
