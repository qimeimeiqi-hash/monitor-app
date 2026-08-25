from unittest.mock import Mock, patch

import pytest
import requests

from src.stock_api import StockApiError, detect_new_low, fetch_daily_closes


def make_chart_response(timestamps, closes, currency="JPY", long_name="ITOCHU Corporation", gmtoffset=32400):
    return {
        "chart": {
            "result": [
                {
                    "meta": {"currency": currency, "longName": long_name, "gmtoffset": gmtoffset},
                    "timestamp": timestamps,
                    "indicators": {"quote": [{"close": closes}]},
                }
            ],
            "error": None,
        }
    }


def test_fetch_daily_closes_returns_parsed_series_on_success():
    mock_response = Mock(status_code=200)
    mock_response.json.return_value = make_chart_response(
        timestamps=[1787472000, 1787558400], closes=[1980.0, 2010.5]
    )

    with patch("src.stock_api.requests.get", return_value=mock_response) as mock_get:
        result = fetch_daily_closes("8001.T")

    assert result["currency"] == "JPY"
    assert result["long_name"] == "ITOCHU Corporation"
    assert [entry["close"] for entry in result["daily_closes"]] == [1980.0, 2010.5]
    assert mock_get.call_args.kwargs["params"]["range"] == "2mo"


def test_fetch_daily_closes_skips_null_close_entries():
    mock_response = Mock(status_code=200)
    mock_response.json.return_value = make_chart_response(
        timestamps=[1787472000, 1787558400, 1787644800], closes=[1980.0, None, 2010.5]
    )

    with patch("src.stock_api.requests.get", return_value=mock_response):
        result = fetch_daily_closes("8001.T")

    assert [entry["close"] for entry in result["daily_closes"]] == [1980.0, 2010.5]


def test_fetch_daily_closes_raises_on_error_status_code():
    mock_response = Mock(status_code=404, text="Not Found")

    with patch("src.stock_api.requests.get", return_value=mock_response):
        with pytest.raises(StockApiError):
            fetch_daily_closes("INVALID.T")


def test_fetch_daily_closes_raises_when_chart_reports_an_error():
    mock_response = Mock(status_code=200)
    mock_response.json.return_value = {"chart": {"result": None, "error": {"description": "No data found"}}}

    with patch("src.stock_api.requests.get", return_value=mock_response):
        with pytest.raises(StockApiError):
            fetch_daily_closes("BADSYMBOL.T")


def test_fetch_daily_closes_raises_on_request_timeout():
    with patch("src.stock_api.requests.get", side_effect=requests.exceptions.Timeout("timed out")):
        with pytest.raises(StockApiError):
            fetch_daily_closes("8001.T")


def test_detect_new_low_returns_event_when_latest_close_is_below_all_others():
    daily_closes = [
        {"date": "2026-07-01", "close": 2000.0},
        {"date": "2026-07-15", "close": 1950.0},
        {"date": "2026-08-25", "close": 1800.0},
    ]

    result = detect_new_low(daily_closes)

    assert result == {"date": "2026-08-25", "close": 1800.0, "previous_low": 1950.0}


def test_detect_new_low_returns_none_when_latest_close_is_not_the_lowest():
    daily_closes = [
        {"date": "2026-07-01", "close": 2000.0},
        {"date": "2026-07-15", "close": 1700.0},
        {"date": "2026-08-25", "close": 1800.0},
    ]

    assert detect_new_low(daily_closes) is None


def test_detect_new_low_returns_none_when_latest_close_only_ties_the_existing_low():
    daily_closes = [
        {"date": "2026-07-01", "close": 2000.0},
        {"date": "2026-07-15", "close": 1800.0},
        {"date": "2026-08-25", "close": 1800.0},
    ]

    assert detect_new_low(daily_closes) is None


def test_detect_new_low_returns_none_with_fewer_than_two_data_points():
    assert detect_new_low([{"date": "2026-08-25", "close": 1800.0}]) is None
    assert detect_new_low([]) is None
