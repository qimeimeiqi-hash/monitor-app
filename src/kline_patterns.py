"""Pure candlestick shape detection. No I/O, no external state.

A candle is a dict with numeric keys: open, high, low, close (volume is unused here).
All thresholds below were confirmed explicitly with the user and must not be changed
without re-confirming, since they define the trading-signal semantics documented in
CLAUDE.md's "股票价格监测" section.
"""

DOJI_BODY_TO_RANGE_RATIO = 0.10
LONG_SHADOW_TO_RANGE_RATIO = 0.40
LONG_SHADOW_TO_BODY_RATIO = 2.0
SHORT_OPPOSITE_SHADOW_TO_RANGE_RATIO = 0.15
LONG_BODY_TO_RANGE_RATIO = 0.70
LONG_BODY_PERCENT_CHANGE = 0.04


def _price_range(candle: dict) -> float:
    return candle["high"] - candle["low"]


def _body_size(candle: dict) -> float:
    return abs(candle["close"] - candle["open"])


def _upper_shadow(candle: dict) -> float:
    return candle["high"] - max(candle["open"], candle["close"])


def _lower_shadow(candle: dict) -> float:
    return min(candle["open"], candle["close"]) - candle["low"]


def _percent_change(candle: dict) -> float:
    return (candle["close"] - candle["open"]) / candle["open"]


def is_doji(candle: dict) -> bool:
    price_range = _price_range(candle)
    if price_range == 0:
        return True
    return _body_size(candle) / price_range <= DOJI_BODY_TO_RANGE_RATIO


def has_long_upper_shadow(candle: dict) -> bool:
    price_range = _price_range(candle)
    if price_range == 0:
        return False
    upper_shadow = _upper_shadow(candle)
    body = _body_size(candle)
    return upper_shadow / price_range >= LONG_SHADOW_TO_RANGE_RATIO and upper_shadow >= LONG_SHADOW_TO_BODY_RATIO * body


def has_long_lower_shadow(candle: dict) -> bool:
    price_range = _price_range(candle)
    if price_range == 0:
        return False
    lower_shadow = _lower_shadow(candle)
    body = _body_size(candle)
    return lower_shadow / price_range >= LONG_SHADOW_TO_RANGE_RATIO and lower_shadow >= LONG_SHADOW_TO_BODY_RATIO * body


def _is_long_candle(candle: dict) -> bool:
    price_range = _price_range(candle)
    body_ratio_long = price_range > 0 and _body_size(candle) / price_range >= LONG_BODY_TO_RANGE_RATIO
    percent_change_long = abs(_percent_change(candle)) >= LONG_BODY_PERCENT_CHANGE
    return body_ratio_long or percent_change_long


def is_long_bullish_candle(candle: dict) -> bool:
    return candle["close"] > candle["open"] and _is_long_candle(candle)


def is_long_bearish_candle(candle: dict) -> bool:
    return candle["close"] < candle["open"] and _is_long_candle(candle)


def is_hammer(candle: dict) -> bool:
    price_range = _price_range(candle)
    if price_range == 0:
        return False
    if not has_long_lower_shadow(candle):
        return False
    return _upper_shadow(candle) / price_range <= SHORT_OPPOSITE_SHADOW_TO_RANGE_RATIO


def is_inverted_hammer(candle: dict) -> bool:
    price_range = _price_range(candle)
    if price_range == 0:
        return False
    if not has_long_upper_shadow(candle):
        return False
    return _lower_shadow(candle) / price_range <= SHORT_OPPOSITE_SHADOW_TO_RANGE_RATIO


def is_bullish_engulfing(previous_candle: dict, current_candle: dict) -> bool:
    previous_is_bearish = previous_candle["close"] < previous_candle["open"]
    current_is_bullish = current_candle["close"] > current_candle["open"]
    if not (previous_is_bearish and current_is_bullish):
        return False
    return current_candle["open"] <= previous_candle["close"] and current_candle["close"] >= previous_candle["open"]


def is_bearish_engulfing(previous_candle: dict, current_candle: dict) -> bool:
    previous_is_bullish = previous_candle["close"] > previous_candle["open"]
    current_is_bearish = current_candle["close"] < current_candle["open"]
    if not (previous_is_bullish and current_is_bearish):
        return False
    return current_candle["open"] >= previous_candle["close"] and current_candle["close"] <= previous_candle["open"]


def is_morning_star(first_candle: dict, second_candle: dict, third_candle: dict) -> bool:
    if not is_long_bearish_candle(first_candle):
        return False
    if not is_doji(second_candle):
        return False
    gapped_down = max(second_candle["open"], second_candle["close"]) < first_candle["close"]
    if not gapped_down:
        return False
    if not is_long_bullish_candle(third_candle):
        return False
    first_body_midpoint = (first_candle["open"] + first_candle["close"]) / 2
    return third_candle["close"] > first_body_midpoint


def is_evening_star(first_candle: dict, second_candle: dict, third_candle: dict) -> bool:
    if not is_long_bullish_candle(first_candle):
        return False
    if not is_doji(second_candle):
        return False
    gapped_up = min(second_candle["open"], second_candle["close"]) > first_candle["close"]
    if not gapped_up:
        return False
    if not is_long_bearish_candle(third_candle):
        return False
    first_body_midpoint = (first_candle["open"] + first_candle["close"]) / 2
    return third_candle["close"] < first_body_midpoint
