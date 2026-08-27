from unittest.mock import Mock, patch

import pytest
import requests

from src.kline_data import KlineDataError, fetch_daily_candles


def make_chart_response(
    timestamps, opens, highs, lows, closes, volumes, currency="JPY", long_name="ITOCHU Corporation", gmtoffset=32400
):
    return {
        "chart": {
            "result": [
                {
                    "meta": {"currency": currency, "longName": long_name, "gmtoffset": gmtoffset},
                    "timestamp": timestamps,
                    "indicators": {
                        "quote": [{"open": opens, "high": highs, "low": lows, "close": closes, "volume": volumes}]
                    },
                }
            ],
            "error": None,
        }
    }


def test_fetch_daily_candles_returns_parsed_ohlcv_series_on_success():
    mock_response = Mock(status_code=200)
    mock_response.json.return_value = make_chart_response(
        timestamps=[1787472000, 1787558400],
        opens=[1970.0, 1985.0],
        highs=[1990.0, 2015.0],
        lows=[1960.0, 1980.0],
        closes=[1980.0, 2010.5],
        volumes=[1_200_000, 1_500_000],
    )

    with patch("src.kline_data.requests.get", return_value=mock_response) as mock_get:
        result = fetch_daily_candles("8001.T")

    assert result["currency"] == "JPY"
    assert result["long_name"] == "ITOCHU Corporation"
    assert result["candles"] == [
        {"date": "2026-08-23", "open": 1970.0, "high": 1990.0, "low": 1960.0, "close": 1980.0, "volume": 1_200_000},
        {"date": "2026-08-24", "open": 1985.0, "high": 2015.0, "low": 1980.0, "close": 2010.5, "volume": 1_500_000},
    ]
    assert mock_get.call_args.kwargs["params"]["range"] == "6mo"


def test_fetch_daily_candles_skips_entries_with_any_missing_field():
    mock_response = Mock(status_code=200)
    mock_response.json.return_value = make_chart_response(
        timestamps=[1787472000, 1787558400, 1787644800],
        opens=[1970.0, None, 2000.0],
        highs=[1990.0, 2020.0, 2020.0],
        lows=[1960.0, 1990.0, 1990.0],
        closes=[1980.0, 2010.5, 2010.0],
        volumes=[1_200_000, 1_500_000, None],
    )

    with patch("src.kline_data.requests.get", return_value=mock_response):
        result = fetch_daily_candles("8001.T")

    assert [candle["date"] for candle in result["candles"]] == ["2026-08-23"]


def test_fetch_daily_candles_raises_on_error_status_code():
    mock_response = Mock(status_code=404, text="Not Found")

    with patch("src.kline_data.requests.get", return_value=mock_response):
        with pytest.raises(KlineDataError):
            fetch_daily_candles("INVALID.T")


def test_fetch_daily_candles_raises_when_chart_reports_an_error():
    mock_response = Mock(status_code=200)
    mock_response.json.return_value = {"chart": {"result": None, "error": {"description": "No data found"}}}

    with patch("src.kline_data.requests.get", return_value=mock_response):
        with pytest.raises(KlineDataError):
            fetch_daily_candles("BADSYMBOL.T")


def test_fetch_daily_candles_raises_on_request_timeout():
    with patch("src.kline_data.requests.get", side_effect=requests.exceptions.Timeout("timed out")):
        with pytest.raises(KlineDataError):
            fetch_daily_candles("8001.T")


def test_fetch_daily_candles_raises_when_no_usable_candles_remain():
    mock_response = Mock(status_code=200)
    mock_response.json.return_value = make_chart_response(
        timestamps=[1787472000],
        opens=[None],
        highs=[None],
        lows=[None],
        closes=[None],
        volumes=[None],
    )

    with patch("src.kline_data.requests.get", return_value=mock_response):
        with pytest.raises(KlineDataError):
            fetch_daily_candles("8001.T")
