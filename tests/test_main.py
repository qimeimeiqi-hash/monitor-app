from pathlib import Path
from unittest.mock import patch

import yaml

from src.fetcher import FetchError
from src.main import run
from src.storage import read_latest_status, read_snapshot


def write_config(config_path: Path, targets: list) -> None:
    config_path.write_text(yaml.safe_dump({"targets": targets}), encoding="utf-8")


def test_run_detects_change_on_second_run_and_notifies_only_for_changed_target(tmp_path, monkeypatch):
    config_path = tmp_path / "targets.yaml"
    data_dir = tmp_path / "data"
    write_config(
        config_path,
        [
            {"name": "Changed Target", "url": "https://a.example.com", "selector": "h1", "enabled": True},
            {"name": "Stable Target", "url": "https://b.example.com", "selector": "h1", "enabled": True},
        ],
    )

    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("NOTIFY_FROM_EMAIL", "from@example.com")
    monkeypatch.setenv("NOTIFY_TO_EMAIL", "to@example.com")

    html_by_url = {
        "https://a.example.com": "<h1>Old Value</h1>",
        "https://b.example.com": "<h1>Same Value</h1>",
    }

    def fake_fetch_html(url, timeout_seconds=15):
        return html_by_url[url]

    with patch("src.main.fetch_html", side_effect=fake_fetch_html):
        first_run_changes = run(config_path=config_path, data_dir=data_dir)

    assert first_run_changes == []

    html_by_url["https://a.example.com"] = "<h1>New Value</h1>"

    with patch("src.main.fetch_html", side_effect=fake_fetch_html), patch(
        "src.main.send_change_notification"
    ) as mock_notify:
        second_run_changes = run(config_path=config_path, data_dir=data_dir)

    assert len(second_run_changes) == 1
    assert second_run_changes[0]["target"] == "Changed Target"
    assert second_run_changes[0]["old_value"] == "Old Value"
    assert second_run_changes[0]["new_value"] == "New Value"
    mock_notify.assert_called_once()

    latest_status = read_latest_status(data_dir)
    latest_status_by_target = {entry["target"]: entry for entry in latest_status}
    assert latest_status_by_target["Changed Target"]["content"] == "New Value"
    assert latest_status_by_target["Stable Target"]["content"] == "Same Value"


def test_run_skips_target_that_fails_to_fetch_without_stopping_other_targets(tmp_path, monkeypatch):
    config_path = tmp_path / "targets.yaml"
    data_dir = tmp_path / "data"
    write_config(
        config_path,
        [
            {"name": "Broken Target", "url": "https://broken.example.com", "selector": "h1", "enabled": True},
            {"name": "Working Target", "url": "https://ok.example.com", "selector": "h1", "enabled": True},
        ],
    )

    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    def fake_fetch_html(url, timeout_seconds=15):
        if url == "https://broken.example.com":
            raise FetchError("simulated network failure")
        return "<h1>Working Content</h1>"

    with patch("src.main.fetch_html", side_effect=fake_fetch_html):
        changes = run(config_path=config_path, data_dir=data_dir)

    assert changes == []
    assert read_snapshot("working-target", data_dir) is not None
    assert read_snapshot("broken-target", data_dir) is None

    latest_status_targets = {entry["target"] for entry in read_latest_status(data_dir)}
    assert latest_status_targets == {"Working Target"}


def test_run_ignores_disabled_targets(tmp_path, monkeypatch):
    config_path = tmp_path / "targets.yaml"
    data_dir = tmp_path / "data"
    write_config(
        config_path,
        [
            {"name": "Disabled Target", "url": "https://disabled.example.com", "selector": "h1", "enabled": False},
        ],
    )
    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    with patch("src.main.fetch_html") as mock_fetch:
        changes = run(config_path=config_path, data_dir=data_dir)

    mock_fetch.assert_not_called()
    assert changes == []
