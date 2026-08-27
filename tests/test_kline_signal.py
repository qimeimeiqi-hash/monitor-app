from src.kline_signal import evaluate_signal


def flat_candle(day_index, open_price=105.0, high=106.0, low=104.0, close=105.0, volume=1000):
    return {"date": f"D{day_index}", "open": open_price, "high": high, "low": low, "close": close, "volume": volume}


def uptrend_ramp_candles(count, base_price=100.0):
    candles = []
    for i in range(count):
        close = base_price + i
        candles.append(
            {"date": f"D{i}", "open": close - 0.5, "high": close + 0.5, "low": close - 1.0, "close": close, "volume": 1000}
        )
    return candles


def downtrend_ramp_candles(count, base_price=200.0):
    candles = []
    for i in range(count):
        close = base_price - i
        candles.append(
            {"date": f"D{i}", "open": close + 0.5, "high": close + 1.0, "low": close - 1.0, "close": close, "volume": 1000}
        )
    return candles


def build_box_window(start_index, upper_touch_high=115.0, lower_touch_low=100.5, flat_count=36):
    window = [flat_candle(start_index + i) for i in range(flat_count)]
    window += [
        flat_candle(start_index + flat_count + i, open_price=110.0, high=upper_touch_high, low=109.0, close=112.0)
        for i in range(2)
    ]
    window += [
        flat_candle(
            start_index + flat_count + 2 + i, open_price=102.0, high=103.0, low=lower_touch_low, close=101.0
        )
        for i in range(2)
    ]
    return window


def test_evaluate_signal_returns_none_when_history_is_too_short():
    candles = [flat_candle(i) for i in range(10)]
    assert evaluate_signal(candles) is None


def test_evaluate_signal_buys_on_hammer_at_recent_low_during_uptrend():
    candles = uptrend_ramp_candles(89)
    today = {
        "date": "D89",
        "open": 188.5,
        "high": 189.5,
        "low": 170.0,
        "close": 189.0,
        "volume": 1000,
    }
    candles.append(today)

    signal = evaluate_signal(candles)

    assert signal["action"] == "buy"
    assert signal["stop_loss"] == 170.0
    assert signal["price"] == 189.0
    assert signal["date"] == "D89"
    assert any("鎚子線" in reason for reason in signal["reasons"])


def test_evaluate_signal_blocks_buy_pattern_during_downtrend():
    candles = downtrend_ramp_candles(89)
    today = {
        "date": "D89",
        "open": 111.5,
        "high": 112.0,
        "low": 100.0,
        "close": 111.0,
        "volume": 1000,
    }
    candles.append(today)

    assert evaluate_signal(candles) is None


def test_evaluate_signal_buys_on_breakout_with_price_and_volume_and_long_candle():
    candles = [flat_candle(i) for i in range(49)]
    candles += build_box_window(49)
    today = {"date": "D89", "open": 110.0, "high": 121.0, "low": 109.5, "close": 120.0, "volume": 2500}
    candles.append(today)

    signal = evaluate_signal(candles)

    assert signal["action"] == "buy"
    assert any("ブレイクアウト" in reason for reason in signal["reasons"])


def test_evaluate_signal_no_breakout_when_volume_confirmation_is_missing():
    candles = [flat_candle(i) for i in range(49)]
    candles += build_box_window(49)
    today = {"date": "D89", "open": 110.0, "high": 121.0, "low": 109.5, "close": 120.0, "volume": 1400}
    candles.append(today)

    assert evaluate_signal(candles) is None


def test_evaluate_signal_sells_on_breakdown_without_needing_volume_confirmation():
    candles = [flat_candle(i) for i in range(49)]
    candles += build_box_window(49)
    today = {"date": "D89", "open": 101.0, "high": 101.5, "low": 97.5, "close": 98.0, "volume": 1000}
    candles.append(today)

    signal = evaluate_signal(candles)

    assert signal["action"] == "sell"
    assert any("下沿を割り込み" in reason for reason in signal["reasons"])


def test_evaluate_signal_sells_on_bearish_engulfing_at_recent_high():
    candles = uptrend_ramp_candles(89)
    today = {"date": "D89", "open": 189.0, "high": 189.5, "low": 185.5, "close": 186.0, "volume": 1000}
    candles.append(today)

    signal = evaluate_signal(candles)

    assert signal["action"] == "sell"
    assert any("陰包陽" in reason for reason in signal["reasons"])
