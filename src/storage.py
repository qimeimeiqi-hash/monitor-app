import json
from pathlib import Path
from typing import Optional


def get_snapshot_path(target_id: str, data_dir: Path) -> Path:
    return data_dir / "snapshots" / f"{target_id}.json"


def read_snapshot(target_id: str, data_dir: Path) -> Optional[dict]:
    snapshot_path = get_snapshot_path(target_id, data_dir)
    if not snapshot_path.exists():
        return None
    with snapshot_path.open("r", encoding="utf-8") as snapshot_file:
        return json.load(snapshot_file)


def write_snapshot(target_id: str, snapshot: dict, data_dir: Path) -> None:
    snapshot_path = get_snapshot_path(target_id, data_dir)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    with snapshot_path.open("w", encoding="utf-8") as snapshot_file:
        json.dump(snapshot, snapshot_file, ensure_ascii=False, indent=2)


def get_history_path(data_dir: Path) -> Path:
    return data_dir / "history.json"


def read_history(data_dir: Path) -> list:
    history_path = get_history_path(data_dir)
    if not history_path.exists():
        return []
    with history_path.open("r", encoding="utf-8") as history_file:
        return json.load(history_file)


def append_history(entry: dict, data_dir: Path) -> None:
    history_path = get_history_path(data_dir)
    history = read_history(data_dir)
    history.append(entry)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("w", encoding="utf-8") as history_file:
        json.dump(history, history_file, ensure_ascii=False, indent=2)


def get_latest_status_path(data_dir: Path) -> Path:
    return data_dir / "latest.json"


def read_latest_status(data_dir: Path) -> list:
    latest_status_path = get_latest_status_path(data_dir)
    if not latest_status_path.exists():
        return []
    with latest_status_path.open("r", encoding="utf-8") as latest_status_file:
        return json.load(latest_status_file)


def write_latest_status(entries: list, data_dir: Path) -> None:
    latest_status_path = get_latest_status_path(data_dir)
    latest_status_path.parent.mkdir(parents=True, exist_ok=True)
    with latest_status_path.open("w", encoding="utf-8") as latest_status_file:
        json.dump(entries, latest_status_file, ensure_ascii=False, indent=2)
