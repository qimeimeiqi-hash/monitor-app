from pathlib import Path
from unittest.mock import patch

import yaml

from src.flight_api import FlightApiError
from src.flights_main import process_route, run
from src.storage import read_history, read_latest_status, read_snapshot

ONEWAY_ROUTE = {
    "name": "上海 → 东京 单程",
    "origin": "SHA",
    "destination": "TYO",
    "trip_type": "oneway",
    "look_ahead_days": 21,
    "nonstop_only": True,
    "currency": "CNY",
    "price_threshold": 2000,
    "enabled": True,
}


def write_config(config_path: Path, routes: list) -> None:
    config_path.write_text(yaml.safe_dump({"routes": routes}), encoding="utf-8")


def test_process_route_alerts_the_first_time_price_drops_below_threshold(tmp_path):
    fake_fare = {"price": 1500.0, "currency": "CNY", "departure_date": "2026-09-10", "return_date": None}

    with patch("src.flights_main.find_cheapest_fare", return_value=fake_fare):
        status_record, change_record = process_route(ONEWAY_ROUTE, "fake-token", tmp_path)

    assert status_record["target"] == "上海 → 东京 单程"
    assert "CNY 1500" in status_record["content"]
    assert change_record is not None
    assert change_record["new_value"] == status_record["content"]

    snapshot = read_snapshot("上海-→-东京-单程", tmp_path)
    assert snapshot["last_alert_price"] == 1500.0


def test_process_route_does_not_realert_when_price_is_still_below_threshold_but_not_lower(tmp_path):
    with patch("src.flights_main.find_cheapest_fare", return_value={"price": 1500.0, "currency": "CNY", "departure_date": "2026-09-10", "return_date": None}):
        process_route(ONEWAY_ROUTE, "fake-token", tmp_path)

    with patch("src.flights_main.find_cheapest_fare", return_value={"price": 1800.0, "currency": "CNY", "departure_date": "2026-09-14", "return_date": None}):
        status_record, change_record = process_route(ONEWAY_ROUTE, "fake-token", tmp_path)

    assert change_record is None
    assert "CNY 1800" in status_record["content"]


def test_process_route_alerts_again_when_price_drops_to_a_new_low(tmp_path):
    with patch("src.flights_main.find_cheapest_fare", return_value={"price": 1500.0, "currency": "CNY", "departure_date": "2026-09-10", "return_date": None}):
        process_route(ONEWAY_ROUTE, "fake-token", tmp_path)

    with patch("src.flights_main.find_cheapest_fare", return_value={"price": 1200.0, "currency": "CNY", "departure_date": "2026-09-16", "return_date": None}):
        status_record, change_record = process_route(ONEWAY_ROUTE, "fake-token", tmp_path)

    assert change_record is not None
    assert change_record["old_value"] == "CNY 1500"
    assert "CNY 1200" in change_record["new_value"]


def test_process_route_does_not_alert_when_price_is_above_threshold(tmp_path):
    with patch("src.flights_main.find_cheapest_fare", return_value={"price": 2500.0, "currency": "CNY", "departure_date": "2026-09-10", "return_date": None}):
        status_record, change_record = process_route(ONEWAY_ROUTE, "fake-token", tmp_path)

    assert change_record is None
    assert "CNY 2500" in status_record["content"]


def test_process_route_handles_no_fare_found_without_crashing(tmp_path):
    with patch("src.flights_main.find_cheapest_fare", return_value=None):
        status_record, change_record = process_route(ONEWAY_ROUTE, "fake-token", tmp_path)

    assert change_record is None
    assert "暂无可用运价数据" in status_record["content"]


def test_run_skips_gracefully_when_amadeus_credentials_are_missing(tmp_path, monkeypatch):
    config_path = tmp_path / "flights.yaml"
    data_dir = tmp_path / "data"
    write_config(config_path, [ONEWAY_ROUTE])

    monkeypatch.delenv("AMADEUS_API_KEY", raising=False)
    monkeypatch.delenv("AMADEUS_API_SECRET", raising=False)

    changes = run(config_path=config_path, data_dir=data_dir)

    assert changes == []
    assert not data_dir.exists()


def test_run_writes_latest_status_and_sends_one_notification_for_all_alerts(tmp_path, monkeypatch):
    config_path = tmp_path / "flights.yaml"
    data_dir = tmp_path / "data"
    second_route = dict(ONEWAY_ROUTE, name="大连 → 东京 单程", origin="DLC")
    write_config(config_path, [ONEWAY_ROUTE, second_route])

    monkeypatch.setenv("AMADEUS_API_KEY", "key")
    monkeypatch.setenv("AMADEUS_API_SECRET", "secret")
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("NOTIFY_FROM_EMAIL", "from@example.com")
    monkeypatch.setenv("NOTIFY_TO_EMAIL", "to@example.com")

    fares_by_origin = {
        "SHA": {"price": 1500.0, "currency": "CNY", "departure_date": "2026-09-10", "return_date": None},
        "DLC": {"price": 2500.0, "currency": "CNY", "departure_date": "2026-09-11", "return_date": None},
    }

    def fake_find_cheapest_fare(origin, **kwargs):
        return fares_by_origin[origin]

    with patch("src.flights_main.get_access_token", return_value="fake-token"), patch(
        "src.flights_main.find_cheapest_fare", side_effect=fake_find_cheapest_fare
    ), patch("src.flights_main.send_change_notification") as mock_notify:
        changes = run(config_path=config_path, data_dir=data_dir)

    assert len(changes) == 1
    assert changes[0]["target"] == "上海 → 东京 单程"
    mock_notify.assert_called_once()

    latest_status = read_latest_status(data_dir)
    assert {entry["target"] for entry in latest_status} == {"上海 → 东京 单程", "大连 → 东京 单程"}
    assert read_history(data_dir) == changes


def test_run_skips_one_broken_route_without_stopping_the_others(tmp_path, monkeypatch):
    config_path = tmp_path / "flights.yaml"
    data_dir = tmp_path / "data"
    broken_route = dict(ONEWAY_ROUTE, name="损坏路线", origin="XXX")
    write_config(config_path, [broken_route, ONEWAY_ROUTE])

    monkeypatch.setenv("AMADEUS_API_KEY", "key")
    monkeypatch.setenv("AMADEUS_API_SECRET", "secret")
    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    def fake_find_cheapest_fare(origin, **kwargs):
        if origin == "XXX":
            raise FlightApiError("simulated Amadeus failure")
        return {"price": 2500.0, "currency": "CNY", "departure_date": "2026-09-10", "return_date": None}

    with patch("src.flights_main.get_access_token", return_value="fake-token"), patch(
        "src.flights_main.find_cheapest_fare", side_effect=fake_find_cheapest_fare
    ):
        changes = run(config_path=config_path, data_dir=data_dir)

    assert changes == []
    latest_status_targets = {entry["target"] for entry in read_latest_status(data_dir)}
    assert latest_status_targets == {"上海 → 东京 单程"}
