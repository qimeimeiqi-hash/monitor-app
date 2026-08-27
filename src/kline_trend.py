"""Trend, box-range, and volume utilities built on top of daily OHLCV candles.

A candle is a dict with keys: open, high, low, close, volume. Candle lists are
expected in ascending date order, with the most recent candle last. All windowed
functions look at the trailing N candles *excluding* the most recent one (today),
matching the "近N个交易日" phrasing confirmed with the user.
"""

SMA_SHORT_WINDOW = 20
SMA_LONG_WINDOW = 60
SMA_SHORT_SLOPE_LOOKBACK = 5
SMA_LONG_SLOPE_LOOKBACK = 10

BOX_LOOKBACK_DAYS = 40
BOX_WIDTH_RATIO_MAX = 0.15
BOX_TOUCH_MIN_COUNT = 2
BOX_TOUCH_TOLERANCE = 0.03

NEAR_EXTREME_LOOKBACK_DAYS = 20
NEAR_EXTREME_TOLERANCE = 0.03

VOLUME_AVERAGE_WINDOW = 20
VOLUME_SURGE_MULTIPLIER = 1.5
VOLUME_SHRINK_MULTIPLIER = 0.6


def compute_sma(values: list, window: int) -> list:
    result = []
    for index in range(len(values)):
        if index < window - 1:
            result.append(None)
        else:
            result.append(sum(values[index - window + 1 : index + 1]) / window)
    return result


def classify_trend(candles: list) -> str:
    closes = [candle["close"] for candle in candles]
    if len(closes) < SMA_LONG_WINDOW + SMA_LONG_SLOPE_LOOKBACK:
        return "range"

    sma_short = compute_sma(closes, SMA_SHORT_WINDOW)
    sma_long = compute_sma(closes, SMA_LONG_WINDOW)

    today_short = sma_short[-1]
    today_long = sma_long[-1]
    short_previous = sma_short[-1 - SMA_SHORT_SLOPE_LOOKBACK]
    long_previous = sma_long[-1 - SMA_LONG_SLOPE_LOOKBACK]
    today_close = closes[-1]

    is_uptrend = (
        today_short > today_long
        and today_short > short_previous
        and today_long >= long_previous
        and today_close > today_short
    )
    if is_uptrend:
        return "uptrend"

    is_downtrend = (
        today_short < today_long
        and today_short < short_previous
        and today_long <= long_previous
        and today_close < today_short
    )
    if is_downtrend:
        return "downtrend"

    return "range"


def find_box_range(candles: list, lookback_days: int = BOX_LOOKBACK_DAYS) -> dict:
    if len(candles) < lookback_days + 1:
        return None

    window = candles[-(lookback_days + 1) : -1]
    max_high = max(candle["high"] for candle in window)
    min_low = min(candle["low"] for candle in window)
    width_ratio = (max_high - min_low) / min_low

    upper_touch_count = sum(1 for candle in window if candle["high"] >= max_high * (1 - BOX_TOUCH_TOLERANCE))
    lower_touch_count = sum(1 for candle in window if candle["low"] <= min_low * (1 + BOX_TOUCH_TOLERANCE))

    qualifies = (
        width_ratio <= BOX_WIDTH_RATIO_MAX
        and upper_touch_count >= BOX_TOUCH_MIN_COUNT
        and lower_touch_count >= BOX_TOUCH_MIN_COUNT
    )
    return {"upper": max_high, "lower": min_low, "qualifies": qualifies}


def is_near_recent_low(candles: list, lookback_days: int = NEAR_EXTREME_LOOKBACK_DAYS) -> bool:
    if len(candles) < lookback_days + 1:
        return False
    window = candles[-(lookback_days + 1) : -1]
    today = candles[-1]
    min_low = min(candle["low"] for candle in window)
    return today["low"] <= min_low * (1 + NEAR_EXTREME_TOLERANCE)


def is_near_recent_high(candles: list, lookback_days: int = NEAR_EXTREME_LOOKBACK_DAYS) -> bool:
    if len(candles) < lookback_days + 1:
        return False
    window = candles[-(lookback_days + 1) : -1]
    today = candles[-1]
    max_high = max(candle["high"] for candle in window)
    return today["high"] >= max_high * (1 - NEAR_EXTREME_TOLERANCE)


def has_volume_surge(
    candles: list, multiplier: float = VOLUME_SURGE_MULTIPLIER, avg_window: int = VOLUME_AVERAGE_WINDOW
) -> bool:
    if len(candles) < avg_window + 1:
        return False
    window = candles[-(avg_window + 1) : -1]
    today = candles[-1]
    average_volume = sum(candle["volume"] for candle in window) / len(window)
    return today["volume"] >= multiplier * average_volume


def has_volume_shrink(
    candles: list, multiplier: float = VOLUME_SHRINK_MULTIPLIER, avg_window: int = VOLUME_AVERAGE_WINDOW
) -> bool:
    if len(candles) < avg_window + 1:
        return False
    window = candles[-(avg_window + 1) : -1]
    today = candles[-1]
    average_volume = sum(candle["volume"] for candle in window) / len(window)
    return today["volume"] <= multiplier * average_volume
