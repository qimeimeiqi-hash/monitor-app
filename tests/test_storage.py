from pathlib import Path

from src.storage import (
    append_history,
    read_history,
    read_latest_status,
    read_snapshot,
    write_latest_status,
    write_snapshot,
)


def test_read_snapshot_returns_none_when_no_snapshot_exists(tmp_path: Path):
    assert read_snapshot("missing-target", tmp_path) is None


def test_write_snapshot_then_read_snapshot_returns_same_data(tmp_path: Path):
    snapshot = {
        "content": "hello",
        "content_hash": "abc123",
        "checked_at": "2026-01-01T00:00:00+00:00",
    }

    write_snapshot("target-a", snapshot, tmp_path)
    result = read_snapshot("target-a", tmp_path)

    assert result == snapshot


def test_append_history_preserves_existing_entries(tmp_path: Path):
    first_entry = {"target": "A", "changed_at": "2026-01-01T00:00:00+00:00"}
    second_entry = {"target": "B", "changed_at": "2026-01-02T00:00:00+00:00"}

    append_history(first_entry, tmp_path)
    append_history(second_entry, tmp_path)

    history = read_history(tmp_path)

    assert history == [first_entry, second_entry]


def test_read_latest_status_returns_empty_list_when_no_file_exists(tmp_path: Path):
    assert read_latest_status(tmp_path) == []


def test_write_latest_status_then_read_latest_status_returns_same_data(tmp_path: Path):
    entries = [
        {"target": "A", "url": "https://a.example.com", "content": "hi", "checked_at": "2026-01-01T00:00:00+00:00"},
    ]

    write_latest_status(entries, tmp_path)
    result = read_latest_status(tmp_path)

    assert result == entries


def test_write_latest_status_overwrites_previous_entries_instead_of_appending(tmp_path: Path):
    write_latest_status([{"target": "Old"}], tmp_path)
    write_latest_status([{"target": "New"}], tmp_path)

    result = read_latest_status(tmp_path)

    assert result == [{"target": "New"}]
