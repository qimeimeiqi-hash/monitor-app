from src.kline_patterns import (
    has_long_lower_shadow,
    has_long_upper_shadow,
    is_bearish_engulfing,
    is_bullish_engulfing,
    is_doji,
    is_evening_star,
    is_hammer,
    is_inverted_hammer,
    is_long_bearish_candle,
    is_long_bullish_candle,
    is_morning_star,
)


def candle(open_price, high, low, close, volume=1000):
    return {"open": open_price, "high": high, "low": low, "close": close, "volume": volume}


def test_is_doji_true_when_body_exactly_ten_percent_of_range():
    assert is_doji(candle(open_price=100.0, high=110.0, low=100.0, close=101.0)) is True


def test_is_doji_false_when_body_slightly_exceeds_ten_percent_of_range():
    assert is_doji(candle(open_price=100.0, high=110.0, low=100.0, close=101.1)) is False


def test_is_doji_true_when_open_equals_high_equals_low_equals_close():
    assert is_doji(candle(open_price=100.0, high=100.0, low=100.0, close=100.0)) is True


def test_has_long_upper_shadow_true_at_exact_boundary():
    # L=100, U=40 (U/L=0.40), B=2 (U>=2*B), lower shadow=58
    assert has_long_upper_shadow(candle(open_price=60.0, high=100.0, low=0.0, close=58.0)) is True


def test_has_long_upper_shadow_false_when_upper_shadow_ratio_below_threshold():
    assert has_long_upper_shadow(candle(open_price=60.0, high=99.0, low=0.0, close=58.0)) is False


def test_has_long_upper_shadow_false_when_body_too_large_relative_to_shadow():
    # U=40 (ratio 0.40 satisfied) but B=25 so U(40) < 2*B(50)
    assert has_long_upper_shadow(candle(open_price=60.0, high=100.0, low=0.0, close=35.0)) is False


def test_has_long_lower_shadow_true_at_exact_boundary():
    assert has_long_lower_shadow(candle(open_price=40.0, high=100.0, low=0.0, close=42.0)) is True


def test_has_long_lower_shadow_false_when_lower_shadow_ratio_below_threshold():
    assert has_long_lower_shadow(candle(open_price=45.0, high=100.0, low=10.0, close=47.0)) is False


def test_is_long_bullish_candle_true_when_body_ratio_meets_seventy_percent():
    assert is_long_bullish_candle(candle(open_price=100.0, high=170.0, low=100.0, close=170.0)) is True


def test_is_long_bullish_candle_true_when_percent_change_meets_four_percent_even_if_body_ratio_low():
    # body/open = 4% exactly, but body/range is small
    assert is_long_bullish_candle(candle(open_price=100.0, high=200.0, low=90.0, close=104.0)) is True


def test_is_long_bullish_candle_false_when_bearish():
    assert is_long_bullish_candle(candle(open_price=170.0, high=170.0, low=100.0, close=100.0)) is False


def test_is_long_bearish_candle_true_when_body_ratio_meets_seventy_percent():
    assert is_long_bearish_candle(candle(open_price=170.0, high=170.0, low=100.0, close=100.0)) is True


def test_is_hammer_true_with_long_lower_shadow_and_short_upper_shadow():
    # L=100 low=0 high=100, body between 42-40=2 -> D=40 (ratio .40, D>=2B), U=100-42=58... need U/L<=0.15
    assert is_hammer(candle(open_price=42.0, high=48.0, low=0.0, close=40.0)) is True


def test_is_hammer_false_when_opposite_shadow_too_long():
    assert is_hammer(candle(open_price=42.0, high=90.0, low=0.0, close=40.0)) is False


def test_is_inverted_hammer_true_with_long_upper_shadow_and_short_lower_shadow():
    assert is_inverted_hammer(candle(open_price=58.0, high=100.0, low=52.0, close=60.0)) is True


def test_is_inverted_hammer_false_when_opposite_shadow_too_long():
    assert is_inverted_hammer(candle(open_price=58.0, high=100.0, low=0.0, close=60.0)) is False


def test_is_bullish_engulfing_true_when_current_body_fully_contains_previous():
    previous = candle(open_price=110.0, high=112.0, low=98.0, close=100.0)
    current = candle(open_price=100.0, high=116.0, low=99.0, close=112.0)
    assert is_bullish_engulfing(previous, current) is True


def test_is_bullish_engulfing_false_when_current_open_above_previous_close():
    previous = candle(open_price=110.0, high=112.0, low=98.0, close=100.0)
    current = candle(open_price=101.0, high=116.0, low=99.0, close=112.0)
    assert is_bullish_engulfing(previous, current) is False


def test_is_bullish_engulfing_false_when_previous_candle_is_not_bearish():
    previous = candle(open_price=100.0, high=112.0, low=98.0, close=110.0)
    current = candle(open_price=100.0, high=116.0, low=99.0, close=112.0)
    assert is_bullish_engulfing(previous, current) is False


def test_is_bearish_engulfing_true_when_current_body_fully_contains_previous():
    previous = candle(open_price=100.0, high=112.0, low=98.0, close=110.0)
    current = candle(open_price=112.0, high=116.0, low=97.0, close=99.0)
    assert is_bearish_engulfing(previous, current) is True


def test_is_morning_star_true_for_classic_three_candle_reversal():
    first = candle(open_price=120.0, high=121.0, low=99.0, close=100.0)
    second = candle(open_price=95.0, high=96.0, low=94.0, close=95.05)
    third = candle(open_price=97.0, high=118.0, low=96.0, close=115.0)
    assert is_morning_star(first, second, third) is True


def test_is_morning_star_false_when_second_candle_does_not_gap_down():
    first = candle(open_price=120.0, high=121.0, low=99.0, close=100.0)
    second = candle(open_price=105.0, high=106.0, low=104.0, close=105.05)
    third = candle(open_price=97.0, high=118.0, low=96.0, close=115.0)
    assert is_morning_star(first, second, third) is False


def test_is_evening_star_true_for_classic_three_candle_reversal():
    first = candle(open_price=100.0, high=121.0, low=99.0, close=120.0)
    second = candle(open_price=124.0, high=126.0, low=123.0, close=124.05)
    third = candle(open_price=123.0, high=124.0, low=102.0, close=105.0)
    assert is_evening_star(first, second, third) is True


def test_is_evening_star_false_when_third_candle_does_not_close_below_midpoint():
    first = candle(open_price=100.0, high=121.0, low=99.0, close=120.0)
    second = candle(open_price=124.0, high=126.0, low=123.0, close=124.05)
    third = candle(open_price=123.0, high=124.0, low=115.0, close=118.0)
    assert is_evening_star(first, second, third) is False
