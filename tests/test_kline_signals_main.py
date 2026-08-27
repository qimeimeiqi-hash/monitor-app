from pathlib import Path
from unittest.mock import patch

import yaml

from src.kline_data import KlineDataError
from src.kline_signals_main import process_stock, run
from src.storage import read_history, read_latest_status, read_snapshot

STOCK = {"name": "伊藤忠商事", "symbol": "8001.T", "enabled": True}


def flat_candle(day_index, open_price=105.0, high=106.0, low=104.0, close=105.0, volume=1000):
    return {"date": f"D{day_index:03d}", "open": open_price, "high": high, "low": low, "close": close, "volume": volume}


def build_box_window(start_index, upper_touch_high=115.0, lower_touch_low=100.5, flat_count=36):
    window = [flat_candle(start_index + i) for i in range(flat_count)]
    window += [
        flat_candle(start_index + flat_count + i, open_price=110.0, high=upper_touch_high, low=109.0, close=112.0)
        for i in range(2)
    ]
    window += [
        flat_candle(start_index + flat_count + 2 + i, open_price=102.0, high=103.0, low=lower_touch_low, close=101.0)
        for i in range(2)
    ]
    return window


def breakout_candle_data(today_index=89, today_close=120.0, currency="JPY"):
    candles = [flat_candle(i) for i in range(49)]
    candles += build_box_window(49)
    candles.append(
        {"date": f"D{today_index:03d}", "open": 110.0, "high": 121.0, "low": 109.5, "close": today_close, "volume": 2500}
    )
    return {"currency": currency, "long_name": "ITOCHU Corporation", "candles": candles}


def no_signal_data():
    candles = [flat_candle(i) for i in range(80)]
    return {"currency": "JPY", "long_name": "ITOCHU Corporation", "candles": candles}


def write_config(config_path: Path, stocks: list) -> None:
    config_path.write_text(yaml.safe_dump({"stocks": stocks}), encoding="utf-8")


def test_process_stock_alerts_on_breakout_buy_signal(tmp_path):
    data = breakout_candle_data()

    with patch("src.kline_signals_main.fetch_daily_candles", return_value=data):
        status_record, signal_record = process_stock(STOCK, tmp_path)

    assert status_record["target"] == "伊藤忠商事"
    assert signal_record is not None
    assert signal_record["action"] == "buy"
    assert any("ブレイクアウト" in reason for reason in signal_record["reasons"])

    snapshot = read_snapshot("8001-t", tmp_path)
    assert snapshot["last_alert_action"] == "buy"


def test_process_stock_returns_no_signal_when_nothing_triggers(tmp_path):
    data = no_signal_data()

    with patch("src.kline_signals_main.fetch_daily_candles", return_value=data):
        status_record, signal_record = process_stock(STOCK, tmp_path)

    assert signal_record is None
    assert status_record["content"]


def test_process_stock_does_not_realert_for_the_same_day_and_action(tmp_path):
    data = breakout_candle_data()

    with patch("src.kline_signals_main.fetch_daily_candles", return_value=data):
        process_stock(STOCK, tmp_path)
        status_record, signal_record = process_stock(STOCK, tmp_path)

    assert signal_record is None
    assert status_record["target"] == "伊藤忠商事"


def test_process_stock_alerts_again_on_a_new_trading_day(tmp_path):
    first_data = breakout_candle_data(today_index=89)
    second_data = breakout_candle_data(today_index=90)

    with patch("src.kline_signals_main.fetch_daily_candles", return_value=first_data):
        process_stock(STOCK, tmp_path)

    with patch("src.kline_signals_main.fetch_daily_candles", return_value=second_data):
        status_record, signal_record = process_stock(STOCK, tmp_path)

    assert signal_record is not None
    assert signal_record["action"] == "buy"


def test_run_skips_one_broken_stock_without_stopping_the_others(tmp_path, monkeypatch):
    config_path = tmp_path / "kline_signals.yaml"
    data_dir = tmp_path / "data"
    broken_stock = {"name": "损坏代码", "symbol": "BROKEN.T", "enabled": True}
    write_config(config_path, [broken_stock, STOCK])

    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    def fake_fetch(symbol, **kwargs):
        if symbol == "BROKEN.T":
            raise KlineDataError("simulated Yahoo Finance failure")
        return no_signal_data()

    with patch("src.kline_signals_main.fetch_daily_candles", side_effect=fake_fetch):
        signals = run(config_path=config_path, data_dir=data_dir)

    assert signals == []
    latest_status_targets = {entry["target"] for entry in read_latest_status(data_dir)}
    assert latest_status_targets == {"伊藤忠商事"}


def test_run_sends_notification_and_appends_history_when_a_signal_fires(tmp_path, monkeypatch):
    config_path = tmp_path / "kline_signals.yaml"
    data_dir = tmp_path / "data"
    second_stock = {"name": "三菱商事", "symbol": "8058.T", "enabled": True}
    write_config(config_path, [STOCK, second_stock])

    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("NOTIFY_FROM_EMAIL", "from@example.com")
    monkeypatch.setenv("NOTIFY_TO_EMAIL", "to@example.com")

    data_by_symbol = {
        "8001.T": breakout_candle_data(),
        "8058.T": no_signal_data(),
    }

    def fake_fetch(symbol, **kwargs):
        return data_by_symbol[symbol]

    with patch("src.kline_signals_main.fetch_daily_candles", side_effect=fake_fetch), patch(
        "src.kline_signals_main.send_signal_notification"
    ) as mock_notify:
        signals = run(config_path=config_path, data_dir=data_dir)

    assert len(signals) == 1
    assert signals[0]["target"] == "伊藤忠商事"
    mock_notify.assert_called_once()
    assert read_history(data_dir) == signals
