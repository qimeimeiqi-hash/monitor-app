import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import yaml
from dotenv import load_dotenv

from src.flight_api import FlightApiError, find_cheapest_fare, get_access_token
from src.notifier import NotificationError, send_change_notification
from src.storage import append_history, read_snapshot, write_latest_status, write_snapshot

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "flights.yaml"
# Separate from docs/data/ (the webpage monitor's directory) so the two monitors
# never overwrite each other's latest.json when their workflows run independently.
DEFAULT_DATA_DIR = PROJECT_ROOT / "docs" / "data" / "flights"


def load_routes(config_path: Path) -> list:
    with config_path.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file) or {}
    return [route for route in config.get("routes", []) if route.get("enabled", True)]


def make_route_id(route: dict) -> str:
    return route["name"].strip().lower().replace(" ", "-")


def build_search_link(origin: str, destination: str, departure_date: str, return_date: Optional[str]) -> str:
    query = f"Flights from {origin} to {destination} on {departure_date}"
    if return_date:
        query += f" returning {return_date}"
    return f"https://www.google.com/travel/flights?q={quote(query)}"


def format_price_label(fare: dict) -> str:
    price_text = f"{fare['currency']} {fare['price']:.0f}"
    if fare.get("return_date"):
        return f"{price_text}（{fare['departure_date']} 出发 / {fare['return_date']} 返程）"
    return f"{price_text}（{fare['departure_date']} 出发）"


def process_route(route: dict, access_token: str, data_dir: Path) -> tuple:
    route_id = make_route_id(route)
    one_way = route["trip_type"] == "oneway"

    today = datetime.now(timezone.utc).date()
    departure_from = (today + timedelta(days=1)).isoformat()
    departure_to = (today + timedelta(days=route.get("look_ahead_days", 21))).isoformat()

    duration_range = None
    if not one_way:
        min_stay = route.get("min_stay_days", 3)
        max_stay = route.get("max_stay_days", 14)
        duration_range = f"{min_stay},{max_stay}"

    fare = find_cheapest_fare(
        access_token=access_token,
        origin=route["origin"],
        destination=route["destination"],
        departure_date_from=departure_from,
        departure_date_to=departure_to,
        one_way=one_way,
        nonstop_only=route.get("nonstop_only", True),
        currency=route.get("currency", "CNY"),
        duration_range=duration_range,
    )

    checked_at = datetime.now(timezone.utc).isoformat()

    if fare is None:
        status_record = {
            "target": route["name"],
            "url": build_search_link(route["origin"], route["destination"], departure_from, None),
            "content": "暂无可用运价数据（该日期区间没有查到直飞报价）",
            "checked_at": checked_at,
        }
        return status_record, None

    status_record = {
        "target": route["name"],
        "url": build_search_link(route["origin"], route["destination"], fare["departure_date"], fare.get("return_date")),
        "content": format_price_label(fare),
        "checked_at": checked_at,
    }

    previous_snapshot = read_snapshot(route_id, data_dir)
    previous_alert_price = previous_snapshot.get("last_alert_price") if previous_snapshot else None
    threshold = route.get("price_threshold")

    should_alert = (
        threshold is not None
        and fare["price"] < threshold
        and (previous_alert_price is None or fare["price"] < previous_alert_price)
    )

    new_alert_price = fare["price"] if should_alert else previous_alert_price
    write_snapshot(
        route_id,
        {"last_price": fare["price"], "last_alert_price": new_alert_price, "checked_at": checked_at},
        data_dir,
    )

    if not should_alert:
        return status_record, None

    change_record = {
        "target": route["name"],
        "url": status_record["url"],
        "changed_at": checked_at,
        "old_value": f"{fare['currency']} {previous_alert_price:.0f}" if previous_alert_price is not None else "此前未低于阈值",
        "new_value": format_price_label(fare),
    }
    append_history(change_record, data_dir)
    return status_record, change_record


def notify_flight_alerts(changes: list) -> None:
    api_key = os.environ.get("RESEND_API_KEY")
    from_email = os.environ.get("NOTIFY_FROM_EMAIL")
    to_email = os.environ.get("NOTIFY_TO_EMAIL")

    if not (api_key and from_email and to_email):
        print("[WARN] Missing Resend email environment variables; skipping flight notification")
        return

    try:
        send_change_notification(changes, api_key=api_key, from_email=from_email, to_email=to_email)
    except NotificationError as notification_error:
        print(f"[ERROR] Failed to send flight notification email: {notification_error}")


def run(config_path: Path = DEFAULT_CONFIG_PATH, data_dir: Path = DEFAULT_DATA_DIR) -> list:
    load_dotenv()
    routes = load_routes(config_path)
    changes = []
    latest_status = []

    api_key = os.environ.get("AMADEUS_API_KEY")
    api_secret = os.environ.get("AMADEUS_API_SECRET")
    if not (api_key and api_secret):
        print("[WARN] Missing AMADEUS_API_KEY/AMADEUS_API_SECRET; skipping flight price check")
        return changes

    try:
        access_token = get_access_token(api_key, api_secret)
    except FlightApiError as auth_error:
        print(f"[ERROR] Failed to authenticate with Amadeus: {auth_error}")
        return changes

    for route in routes:
        try:
            status_record, change_record = process_route(route, access_token, data_dir)
        except FlightApiError as route_error:
            print(f"[WARN] Skipped route '{route.get('name')}': {route_error}")
            continue

        latest_status.append(status_record)
        if change_record is not None:
            changes.append(change_record)

    write_latest_status(latest_status, data_dir)

    if changes:
        notify_flight_alerts(changes)

    return changes


if __name__ == "__main__":
    run()
