import json
import os
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv

from src.kline_data import KlineDataError, fetch_daily_candles
from src.kline_signal import evaluate_signal
from src.kline_trend import classify_trend
from src.notifier import NotificationError, send_signal_notification
from src.storage import append_history, read_snapshot, write_latest_status, write_snapshot

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "kline_signals.yaml"
# Fully independent from docs/data/stocks/ (2か月最安値監視) and docs/data/
# (Webページ監視) so this system never shares snapshots/history/latest with them.
DEFAULT_DATA_DIR = PROJECT_ROOT / "docs" / "data" / "kline"

TREND_LABELS = {"uptrend": "上昇", "downtrend": "下降", "range": "レンジ"}


def load_stocks(config_path: Path) -> list:
    with config_path.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file) or {}
    return [stock for stock in config.get("stocks", []) if stock.get("enabled", True)]


def make_stock_id(stock: dict) -> str:
    return stock["symbol"].strip().lower().replace(".", "-")


def build_quote_link(symbol: str) -> str:
    return f"https://finance.yahoo.com/quote/{symbol}"


def format_price_label(currency: str, price: float, date: str) -> str:
    return f"{currency} {price:.1f}（{date} 終値）"


def write_candles(stock_id: str, candles: list, data_dir: Path) -> None:
    candles_path = data_dir / "candles" / f"{stock_id}.json"
    candles_path.parent.mkdir(parents=True, exist_ok=True)
    with candles_path.open("w", encoding="utf-8") as candles_file:
        json.dump(candles, candles_file, ensure_ascii=False, indent=2)


def process_stock(stock: dict, data_dir: Path) -> tuple:
    price_data = fetch_daily_candles(stock["symbol"])
    candles = price_data["candles"]
    today = candles[-1]
    checked_at = datetime.now(timezone.utc).isoformat()
    currency = price_data["currency"]
    trend_label = TREND_LABELS[classify_trend(candles)]

    stock_id = make_stock_id(stock)
    write_candles(stock_id, candles, data_dir)

    status_record = {
        "id": stock_id,
        "target": stock["name"],
        "url": build_quote_link(stock["symbol"]),
        "content": f"トレンド: {trend_label} ／ {format_price_label(currency, today['close'], today['date'])}",
        "checked_at": checked_at,
    }

    signal = evaluate_signal(candles)
    if signal is None:
        return status_record, None

    previous_snapshot = read_snapshot(stock_id, data_dir)
    already_alerted = (
        previous_snapshot is not None
        and previous_snapshot.get("last_alert_date") == signal["date"]
        and previous_snapshot.get("last_alert_action") == signal["action"]
    )
    if already_alerted:
        return status_record, None

    write_snapshot(
        stock_id,
        {"last_alert_date": signal["date"], "last_alert_action": signal["action"], "checked_at": checked_at},
        data_dir,
    )

    stop_loss_label = format_price_label(currency, signal["stop_loss"], signal["date"]) if signal["stop_loss"] is not None else None
    signal_record = {
        "target": stock["name"],
        "url": status_record["url"],
        "changed_at": checked_at,
        "action": signal["action"],
        "price_label": format_price_label(currency, signal["price"], signal["date"]),
        "reasons": signal["reasons"],
        "stop_loss_label": stop_loss_label,
    }
    append_history(signal_record, data_dir)
    return status_record, signal_record


def notify_signals(signals: list) -> None:
    api_key = os.environ.get("RESEND_API_KEY")
    from_email = os.environ.get("NOTIFY_FROM_EMAIL")
    to_email = os.environ.get("NOTIFY_TO_EMAIL")

    if not (api_key and from_email and to_email):
        print("[WARN] Missing Resend email environment variables; skipping K-line signal notification")
        return

    try:
        send_signal_notification(signals, api_key=api_key, from_email=from_email, to_email=to_email)
    except NotificationError as notification_error:
        print(f"[ERROR] Failed to send K-line signal notification email: {notification_error}")


def run(config_path: Path = DEFAULT_CONFIG_PATH, data_dir: Path = DEFAULT_DATA_DIR) -> list:
    load_dotenv()
    stocks = load_stocks(config_path)
    signals = []
    latest_status = []

    for stock in stocks:
        try:
            status_record, signal_record = process_stock(stock, data_dir)
        except KlineDataError as kline_error:
            print(f"[WARN] Skipped stock '{stock.get('name')}': {kline_error}")
            continue

        latest_status.append(status_record)
        if signal_record is not None:
            signals.append(signal_record)

    write_latest_status(latest_status, data_dir)

    if signals:
        notify_signals(signals)

    return signals


if __name__ == "__main__":
    run()
