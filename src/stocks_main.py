import os
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv

from src.notifier import NotificationError, send_change_notification
from src.stock_api import StockApiError, detect_new_low, fetch_daily_closes
from src.storage import append_history, read_snapshot, write_latest_status, write_snapshot

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "stocks.yaml"
# Separate from docs/data/ so this workflow never clobbers the webpage monitor's
# latest.json (each independently-scheduled workflow overwrites its own file).
DEFAULT_DATA_DIR = PROJECT_ROOT / "docs" / "data" / "stocks"


def load_stocks(config_path: Path) -> list:
    with config_path.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file) or {}
    return [stock for stock in config.get("stocks", []) if stock.get("enabled", True)]


def make_stock_id(stock: dict) -> str:
    return stock["symbol"].strip().lower().replace(".", "-")


def build_quote_link(symbol: str) -> str:
    return f"https://finance.yahoo.com/quote/{symbol}"


def format_price_label(currency: str, close: float, date: str) -> str:
    return f"{currency} {close:.1f}（{date} 終値）"


def process_stock(stock: dict, data_dir: Path) -> tuple:
    price_data = fetch_daily_closes(stock["symbol"])
    latest_entry = price_data["daily_closes"][-1]
    checked_at = datetime.now(timezone.utc).isoformat()
    stock_id = make_stock_id(stock)

    status_record = {
        "id": stock_id,
        "target": stock["name"],
        "url": build_quote_link(stock["symbol"]),
        "content": format_price_label(price_data["currency"], latest_entry["close"], latest_entry["date"]),
        "checked_at": checked_at,
    }

    new_low = detect_new_low(price_data["daily_closes"])
    if new_low is None:
        return status_record, None

    previous_snapshot = read_snapshot(stock_id, data_dir)
    already_alerted_today = previous_snapshot is not None and previous_snapshot.get("last_alert_date") == new_low["date"]
    if already_alerted_today:
        return status_record, None

    write_snapshot(
        stock_id,
        {"last_alert_date": new_low["date"], "last_alert_close": new_low["close"], "checked_at": checked_at},
        data_dir,
    )

    change_record = {
        "target": stock["name"],
        "url": status_record["url"],
        "changed_at": checked_at,
        "old_value": f"直近2か月の最安値 {price_data['currency']} {new_low['previous_low']:.1f}",
        "new_value": format_price_label(price_data["currency"], new_low["close"], new_low["date"]) + "（2か月ぶりの最安値を更新）",
    }
    append_history(change_record, data_dir)
    return status_record, change_record


def notify_new_lows(changes: list) -> None:
    api_key = os.environ.get("RESEND_API_KEY")
    from_email = os.environ.get("NOTIFY_FROM_EMAIL")
    to_email = os.environ.get("NOTIFY_TO_EMAIL")

    if not (api_key and from_email and to_email):
        print("[WARN] Missing Resend email environment variables; skipping stock notification")
        return

    try:
        send_change_notification(changes, api_key=api_key, from_email=from_email, to_email=to_email)
    except NotificationError as notification_error:
        print(f"[ERROR] Failed to send stock notification email: {notification_error}")


def run(config_path: Path = DEFAULT_CONFIG_PATH, data_dir: Path = DEFAULT_DATA_DIR) -> list:
    load_dotenv()
    stocks = load_stocks(config_path)
    changes = []
    latest_status = []

    for stock in stocks:
        try:
            status_record, change_record = process_stock(stock, data_dir)
        except StockApiError as stock_error:
            print(f"[WARN] Skipped stock '{stock.get('name')}': {stock_error}")
            continue

        latest_status.append(status_record)
        if change_record is not None:
            changes.append(change_record)

    write_latest_status(latest_status, data_dir)

    if changes:
        notify_new_lows(changes)

    return changes


if __name__ == "__main__":
    run()
