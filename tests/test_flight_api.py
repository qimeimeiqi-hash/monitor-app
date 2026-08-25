from unittest.mock import Mock, patch

import pytest
import requests

from src.flight_api import FlightApiError, find_cheapest_fare, get_access_token


def test_get_access_token_returns_token_on_success():
    mock_response = Mock(status_code=200)
    mock_response.json.return_value = {"access_token": "test-token-123", "expires_in": 1799}

    with patch("src.flight_api.requests.post", return_value=mock_response) as mock_post:
        token = get_access_token("api-key", "api-secret")

    assert token == "test-token-123"
    called_kwargs = mock_post.call_args.kwargs
    assert called_kwargs["data"]["client_id"] == "api-key"
    assert called_kwargs["data"]["client_secret"] == "api-secret"
    assert called_kwargs["data"]["grant_type"] == "client_credentials"


def test_get_access_token_raises_on_error_response():
    mock_response = Mock(status_code=401, text="invalid client")

    with patch("src.flight_api.requests.post", return_value=mock_response):
        with pytest.raises(FlightApiError):
            get_access_token("bad-key", "bad-secret")


def test_get_access_token_raises_on_request_timeout():
    with patch("src.flight_api.requests.post", side_effect=requests.exceptions.Timeout("timed out")):
        with pytest.raises(FlightApiError):
            get_access_token("api-key", "api-secret")


def test_find_cheapest_fare_returns_none_when_no_offers_available():
    mock_response = Mock(status_code=200)
    mock_response.json.return_value = {"data": []}

    with patch("src.flight_api.requests.get", return_value=mock_response):
        result = find_cheapest_fare(
            access_token="token",
            origin="SHA",
            destination="TYO",
            departure_date_from="2026-09-01",
            departure_date_to="2026-09-21",
            one_way=True,
            nonstop_only=True,
            currency="CNY",
        )

    assert result is None


def test_find_cheapest_fare_returns_the_lowest_priced_offer_among_multiple():
    mock_response = Mock(status_code=200)
    mock_response.json.return_value = {
        "data": [
            {"departureDate": "2026-09-05", "price": {"total": "1800.00"}},
            {"departureDate": "2026-09-12", "price": {"total": "1250.50"}},
            {"departureDate": "2026-09-18", "price": {"total": "1600.00"}},
        ]
    }

    with patch("src.flight_api.requests.get", return_value=mock_response) as mock_get:
        result = find_cheapest_fare(
            access_token="token",
            origin="SHA",
            destination="TYO",
            departure_date_from="2026-09-01",
            departure_date_to="2026-09-21",
            one_way=True,
            nonstop_only=True,
            currency="CNY",
        )

    assert result == {
        "price": 1250.50,
        "currency": "CNY",
        "departure_date": "2026-09-12",
        "return_date": None,
    }
    called_kwargs = mock_get.call_args.kwargs
    assert called_kwargs["params"]["origin"] == "SHA"
    assert called_kwargs["params"]["destination"] == "TYO"
    assert called_kwargs["params"]["oneWay"] == "true"
    assert called_kwargs["params"]["nonStop"] == "true"
    assert called_kwargs["headers"]["Authorization"] == "Bearer token"


def test_find_cheapest_fare_includes_return_date_and_duration_for_roundtrip():
    mock_response = Mock(status_code=200)
    mock_response.json.return_value = {
        "data": [{"departureDate": "2026-09-05", "returnDate": "2026-09-10", "price": {"total": "3200.00"}}]
    }

    with patch("src.flight_api.requests.get", return_value=mock_response) as mock_get:
        result = find_cheapest_fare(
            access_token="token",
            origin="DLC",
            destination="TYO",
            departure_date_from="2026-09-01",
            departure_date_to="2026-09-21",
            one_way=False,
            nonstop_only=True,
            currency="CNY",
            duration_range="3,10",
        )

    assert result["return_date"] == "2026-09-10"
    called_kwargs = mock_get.call_args.kwargs
    assert called_kwargs["params"]["oneWay"] == "false"
    assert called_kwargs["params"]["duration"] == "3,10"


def test_find_cheapest_fare_raises_on_error_response():
    mock_response = Mock(status_code=500, text="internal error")

    with patch("src.flight_api.requests.get", return_value=mock_response):
        with pytest.raises(FlightApiError):
            find_cheapest_fare(
                access_token="token",
                origin="SHA",
                destination="TYO",
                departure_date_from="2026-09-01",
                departure_date_to="2026-09-21",
                one_way=True,
                nonstop_only=True,
                currency="CNY",
            )
