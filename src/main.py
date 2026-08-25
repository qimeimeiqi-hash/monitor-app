import os
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv

from src.differ import compare_content
from src.extractor import ExtractionError, extract_text
from src.fetcher import FetchError, fetch_html
from src.notifier import NotificationError, send_change_notification
from src.storage import append_history, read_snapshot, write_latest_status, write_snapshot

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "targets.yaml"
# Lives under docs/ (not the repo root) because GitHub Pages only publishes the
# configured docs/ source folder — the dashboard can only fetch JSON that sits inside it.
DEFAULT_DATA_DIR = PROJECT_ROOT / "docs" / "data"


def load_targets(config_path: Path) -> list:
    with config_path.open("r", encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file) or {}
    return [target for target in config.get("targets", []) if target.get("enabled", True)]


def make_target_id(target: dict) -> str:
    return target["name"].strip().lower().replace(" ", "-")


def process_target(target: dict, data_dir: Path) -> tuple:
    target_id = make_target_id(target)
    html = fetch_html(target["url"])
    extracted_text = extract_text(html, target["selector"])
    previous_snapshot = read_snapshot(target_id, data_dir)
    diff_result = compare_content(extracted_text, previous_snapshot)

    checked_at = datetime.now(timezone.utc).isoformat()
    write_snapshot(
        target_id,
        {
            "content": diff_result.new_value,
            "content_hash": diff_result.content_hash,
            "checked_at": checked_at,
        },
        data_dir,
    )

    status_record = {
        "target": target["name"],
        "url": target["url"],
        "content": diff_result.new_value,
        "checked_at": checked_at,
    }

    if not diff_result.changed:
        return status_record, None

    change_record = {
        "target": target["name"],
        "url": target["url"],
        "changed_at": checked_at,
        "old_value": diff_result.old_value,
        "new_value": diff_result.new_value,
    }
    append_history(change_record, data_dir)
    return status_record, change_record


def notify_if_configured(changes: list) -> None:
    api_key = os.environ.get("RESEND_API_KEY")
    from_email = os.environ.get("NOTIFY_FROM_EMAIL")
    to_email = os.environ.get("NOTIFY_TO_EMAIL")

    if not (api_key and from_email and to_email):
        print("[WARN] Missing Resend email environment variables; skipping notification")
        return

    try:
        send_change_notification(changes, api_key=api_key, from_email=from_email, to_email=to_email)
    except NotificationError as notification_error:
        print(f"[ERROR] Failed to send notification email: {notification_error}")


def run(config_path: Path = DEFAULT_CONFIG_PATH, data_dir: Path = DEFAULT_DATA_DIR) -> list:
    load_dotenv()
    targets = load_targets(config_path)
    changes = []
    latest_status = []

    for target in targets:
        try:
            status_record, change_record = process_target(target, data_dir)
        except (FetchError, ExtractionError) as target_error:
            print(f"[WARN] Skipped target '{target.get('name')}': {target_error}")
            continue

        latest_status.append(status_record)
        if change_record is not None:
            changes.append(change_record)

    write_latest_status(latest_status, data_dir)

    if changes:
        notify_if_configured(changes)

    return changes


if __name__ == "__main__":
    run()
