from pathlib import Path
from unittest.mock import patch

import yaml

from src.stock_api import StockApiError
from src.stocks_main import process_stock, run
from src.storage import read_history, read_latest_status, read_snapshot

STOCK = {"name": "伊藤忠商事", "symbol": "8001.T", "enabled": True}


def price_data(closes_with_dates, currency="JPY"):
    return {
        "currency": currency,
        "long_name": "ITOCHU Corporation",
        "daily_closes": [{"date": date, "close": close} for date, close in closes_with_dates],
    }


def write_config(config_path: Path, stocks: list) -> None:
    config_path.write_text(yaml.safe_dump({"stocks": stocks}), encoding="utf-8")


def test_process_stock_alerts_when_latest_close_is_a_new_two_month_low(tmp_path):
    data = price_data([("2026-07-01", 2000.0), ("2026-07-20", 1900.0), ("2026-08-25", 1750.0)])

    with patch("src.stocks_main.fetch_daily_closes", return_value=data):
        status_record, change_record = process_stock(STOCK, tmp_path)

    assert status_record["target"] == "伊藤忠商事"
    assert "JPY 1750.0" in status_record["content"]
    assert change_record is not None
    assert "1900.0" in change_record["old_value"]
    assert "1750.0" in change_record["new_value"]
    assert "2か月ぶりの最安値を更新" in change_record["new_value"]

    snapshot = read_snapshot("8001-t", tmp_path)
    assert snapshot["last_alert_date"] == "2026-08-25"


def test_process_stock_does_not_alert_when_latest_close_is_not_a_new_low(tmp_path):
    data = price_data([("2026-07-01", 2000.0), ("2026-07-20", 1900.0), ("2026-08-25", 1950.0)])

    with patch("src.stocks_main.fetch_daily_closes", return_value=data):
        status_record, change_record = process_stock(STOCK, tmp_path)

    assert change_record is None
    assert "JPY 1950.0" in status_record["content"]


def test_process_stock_does_not_realert_for_the_same_trading_day(tmp_path):
    data = price_data([("2026-07-01", 2000.0), ("2026-07-20", 1900.0), ("2026-08-25", 1750.0)])

    with patch("src.stocks_main.fetch_daily_closes", return_value=data):
        process_stock(STOCK, tmp_path)
        status_record, change_record = process_stock(STOCK, tmp_path)

    assert change_record is None
    assert "JPY 1750.0" in status_record["content"]


def test_process_stock_alerts_again_for_a_later_lower_close_on_a_new_day(tmp_path):
    first_run_data = price_data([("2026-07-01", 2000.0), ("2026-07-20", 1900.0), ("2026-08-25", 1750.0)])
    second_run_data = price_data(
        [("2026-07-01", 2000.0), ("2026-07-20", 1900.0), ("2026-08-25", 1750.0), ("2026-08-26", 1600.0)]
    )

    with patch("src.stocks_main.fetch_daily_closes", return_value=first_run_data):
        process_stock(STOCK, tmp_path)

    with patch("src.stocks_main.fetch_daily_closes", return_value=second_run_data):
        status_record, change_record = process_stock(STOCK, tmp_path)

    assert change_record is not None
    assert "1600.0" in change_record["new_value"]


def test_run_skips_one_broken_stock_without_stopping_the_others(tmp_path, monkeypatch):
    config_path = tmp_path / "stocks.yaml"
    data_dir = tmp_path / "data"
    broken_stock = {"name": "损坏代码", "symbol": "BROKEN.T", "enabled": True}
    write_config(config_path, [broken_stock, STOCK])

    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    def fake_fetch(symbol, **kwargs):
        if symbol == "BROKEN.T":
            raise StockApiError("simulated Yahoo Finance failure")
        return price_data([("2026-07-01", 1900.0), ("2026-08-25", 1950.0)])

    with patch("src.stocks_main.fetch_daily_closes", side_effect=fake_fetch):
        changes = run(config_path=config_path, data_dir=data_dir)

    assert changes == []
    latest_status_targets = {entry["target"] for entry in read_latest_status(data_dir)}
    assert latest_status_targets == {"伊藤忠商事"}


def test_run_sends_one_combined_notification_and_appends_history_for_all_new_lows(tmp_path, monkeypatch):
    config_path = tmp_path / "stocks.yaml"
    data_dir = tmp_path / "data"
    second_stock = {"name": "三菱商事", "symbol": "8058.T", "enabled": True}
    write_config(config_path, [STOCK, second_stock])

    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("NOTIFY_FROM_EMAIL", "from@example.com")
    monkeypatch.setenv("NOTIFY_TO_EMAIL", "to@example.com")

    data_by_symbol = {
        "8001.T": price_data([("2026-07-01", 2000.0), ("2026-07-20", 1900.0), ("2026-08-25", 1750.0)]),
        "8058.T": price_data([("2026-07-01", 3000.0), ("2026-07-20", 2900.0), ("2026-08-25", 2950.0)]),
    }

    def fake_fetch(symbol, **kwargs):
        return data_by_symbol[symbol]

    with patch("src.stocks_main.fetch_daily_closes", side_effect=fake_fetch), patch(
        "src.stocks_main.send_change_notification"
    ) as mock_notify:
        changes = run(config_path=config_path, data_dir=data_dir)

    assert len(changes) == 1
    assert changes[0]["target"] == "伊藤忠商事"
    mock_notify.assert_called_once()
    assert read_history(data_dir) == changes
