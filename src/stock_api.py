from datetime import datetime, timedelta, timezone

import requests

YAHOO_CHART_URL_TEMPLATE = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"


class StockApiError(Exception):
    pass


def _timestamp_to_date(unix_timestamp: int, gmtoffset_seconds: int) -> str:
    local_tz = timezone(timedelta(seconds=gmtoffset_seconds))
    return datetime.fromtimestamp(unix_timestamp, tz=local_tz).date().isoformat()


def fetch_daily_closes(symbol: str, range_param: str = "2mo", timeout_seconds: int = 15) -> dict:
    try:
        response = requests.get(
            YAHOO_CHART_URL_TEMPLATE.format(symbol=symbol),
            params={"range": range_param, "interval": "1d"},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=timeout_seconds,
        )
    except requests.RequestException as request_error:
        raise StockApiError(f"Failed to fetch price history for {symbol}: {request_error}") from request_error

    if response.status_code >= 400:
        raise StockApiError(f"Yahoo Finance returned {response.status_code} for {symbol}: {response.text}")

    chart = response.json().get("chart", {})
    if chart.get("error"):
        raise StockApiError(f"Yahoo Finance error for {symbol}: {chart['error']}")

    results = chart.get("result") or []
    if not results:
        raise StockApiError(f"Yahoo Finance returned no chart data for {symbol}")

    result = results[0]
    meta = result.get("meta", {})
    timestamps = result.get("timestamp") or []
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]
    closes = quote.get("close") or []
    gmtoffset_seconds = meta.get("gmtoffset", 0)

    daily_closes = [
        {"date": _timestamp_to_date(ts, gmtoffset_seconds), "close": close}
        for ts, close in zip(timestamps, closes)
        if close is not None
    ]

    if not daily_closes:
        raise StockApiError(f"Yahoo Finance returned no usable close prices for {symbol}")

    return {
        "currency": meta.get("currency", "JPY"),
        "long_name": meta.get("longName"),
        "daily_closes": daily_closes,
    }


def detect_new_low(daily_closes: list) -> dict:
    """Return the new-low event if the most recent close is strictly below every
    other close in the given window, else None. A window of fewer than 2 points
    can't establish a "new" low relative to prior data."""
    if len(daily_closes) < 2:
        return None

    *previous_closes, latest = daily_closes
    previous_low = min(entry["close"] for entry in previous_closes)

    if latest["close"] < previous_low:
        return {"date": latest["date"], "close": latest["close"], "previous_low": previous_low}
    return None
