from src.kline_trend import (
    classify_trend,
    compute_sma,
    find_box_range,
    has_volume_shrink,
    has_volume_surge,
    is_near_recent_high,
    is_near_recent_low,
)


def make_candle(open_price=105.0, high=106.0, low=104.0, close=105.0, volume=1000):
    return {"open": open_price, "high": high, "low": low, "close": close, "volume": volume}


def test_compute_sma_returns_none_for_indices_before_window_is_full():
    result = compute_sma([1, 2, 3, 4, 5], window=3)
    assert result == [None, None, 2, 3, 4]


def test_compute_sma_returns_all_none_when_fewer_values_than_window():
    assert compute_sma([1, 2], window=3) == [None, None]


def test_classify_trend_returns_uptrend_when_moving_averages_rise_and_diverge():
    candles = [make_candle(close=100.0 + i) for i in range(80)]
    assert classify_trend(candles) == "uptrend"


def test_classify_trend_returns_downtrend_when_moving_averages_fall_and_diverge():
    candles = [make_candle(close=200.0 - i) for i in range(80)]
    assert classify_trend(candles) == "downtrend"


def test_classify_trend_returns_range_when_price_is_flat():
    candles = [make_candle(close=100.0) for _ in range(80)]
    assert classify_trend(candles) == "range"


def test_classify_trend_returns_range_when_not_enough_history():
    candles = [make_candle(close=100.0 + i) for i in range(30)]
    assert classify_trend(candles) == "range"


def _build_box_window(upper_touch_high=115.0, lower_touch_low=100.5, flat_count=36):
    window = [make_candle() for _ in range(flat_count)]
    window += [make_candle(open_price=110.0, high=upper_touch_high, low=109.0, close=112.0) for _ in range(2)]
    window += [make_candle(open_price=102.0, high=103.0, low=lower_touch_low, close=101.0) for _ in range(2)]
    return window


def test_find_box_range_qualifies_when_width_and_touch_conditions_are_met():
    window = _build_box_window()
    today = make_candle()
    box = find_box_range(window + [today])

    assert box["qualifies"] is True
    assert box["upper"] == 115.0
    assert box["lower"] == 100.5


def test_find_box_range_does_not_qualify_when_width_exceeds_fifteen_percent():
    window = _build_box_window(upper_touch_high=200.0)
    today = make_candle()
    box = find_box_range(window + [today])

    assert box["qualifies"] is False


def test_find_box_range_does_not_qualify_when_touch_count_is_insufficient():
    window = [make_candle() for _ in range(38)]
    window += [make_candle(open_price=110.0, high=115.0, low=109.0, close=112.0)]
    window += [make_candle(open_price=102.0, high=103.0, low=100.5, close=101.0)]
    today = make_candle()
    box = find_box_range(window + [today])

    assert box["qualifies"] is False


def test_find_box_range_returns_none_when_not_enough_history():
    candles = [make_candle() for _ in range(10)]
    assert find_box_range(candles) is None


def test_is_near_recent_low_true_at_exact_three_percent_boundary():
    window = [make_candle(low=100.0) for _ in range(20)]
    today = make_candle(low=103.0)
    assert is_near_recent_low(window + [today]) is True


def test_is_near_recent_low_false_just_beyond_three_percent_boundary():
    window = [make_candle(low=100.0) for _ in range(20)]
    today = make_candle(low=103.1)
    assert is_near_recent_low(window + [today]) is False


def test_is_near_recent_high_true_at_exact_boundary():
    window = [make_candle(high=100.0) for _ in range(20)]
    today = make_candle(high=97.0)
    assert is_near_recent_high(window + [today]) is True


def test_is_near_recent_high_false_just_below_boundary():
    window = [make_candle(high=100.0) for _ in range(20)]
    today = make_candle(high=96.9)
    assert is_near_recent_high(window + [today]) is False


def test_has_volume_surge_true_at_exact_multiplier_boundary():
    window = [make_candle(volume=1000) for _ in range(20)]
    today = make_candle(volume=1500)
    assert has_volume_surge(window + [today], multiplier=1.5) is True


def test_has_volume_surge_false_just_below_multiplier_boundary():
    window = [make_candle(volume=1000) for _ in range(20)]
    today = make_candle(volume=1499)
    assert has_volume_surge(window + [today], multiplier=1.5) is False


def test_has_volume_shrink_true_at_exact_multiplier_boundary():
    window = [make_candle(volume=1000) for _ in range(20)]
    today = make_candle(volume=600)
    assert has_volume_shrink(window + [today]) is True


def test_has_volume_shrink_false_just_above_multiplier_boundary():
    window = [make_candle(volume=1000) for _ in range(20)]
    today = make_candle(volume=601)
    assert has_volume_shrink(window + [today]) is False
