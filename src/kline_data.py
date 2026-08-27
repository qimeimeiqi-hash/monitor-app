from datetime import datetime, timedelta, timezone

import requests

YAHOO_CHART_URL_TEMPLATE = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
DEFAULT_RANGE = "6mo"


class KlineDataError(Exception):
    pass


def _timestamp_to_date(unix_timestamp: int, gmtoffset_seconds: int) -> str:
    local_tz = timezone(timedelta(seconds=gmtoffset_seconds))
    return datetime.fromtimestamp(unix_timestamp, tz=local_tz).date().isoformat()


def fetch_daily_candles(symbol: str, range_param: str = DEFAULT_RANGE, timeout_seconds: int = 15) -> dict:
    try:
        response = requests.get(
            YAHOO_CHART_URL_TEMPLATE.format(symbol=symbol),
            params={"range": range_param, "interval": "1d"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=timeout_seconds,
        )
    except requests.RequestException as request_error:
        raise KlineDataError(f"Failed to fetch candle history for {symbol}: {request_error}") from request_error

    if response.status_code >= 400:
        raise KlineDataError(f"Yahoo Finance returned {response.status_code} for {symbol}: {response.text}")

    chart = response.json().get("chart", {})
    if chart.get("error"):
        raise KlineDataError(f"Yahoo Finance error for {symbol}: {chart['error']}")

    results = chart.get("result") or []
    if not results:
        raise KlineDataError(f"Yahoo Finance returned no chart data for {symbol}")

    result = results[0]
    meta = result.get("meta", {})
    timestamps = result.get("timestamp") or []
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]
    opens = quote.get("open") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []
    gmtoffset_seconds = meta.get("gmtoffset", 0)

    candles = []
    for timestamp, open_price, high, low, close, volume in zip(timestamps, opens, highs, lows, closes, volumes):
        if None in (open_price, high, low, close, volume):
            continue
        candles.append(
            {
                "date": _timestamp_to_date(timestamp, gmtoffset_seconds),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            }
        )

    if not candles:
        raise KlineDataError(f"Yahoo Finance returned no usable candles for {symbol}")

    return {
        "currency": meta.get("currency", "JPY"),
        "long_name": meta.get("longName"),
        "candles": candles,
    }
