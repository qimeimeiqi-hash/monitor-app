import requests

AMADEUS_AUTH_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
AMADEUS_FLIGHT_DATES_URL = "https://test.api.amadeus.com/v1/shopping/flight-dates"


class FlightApiError(Exception):
    pass


def get_access_token(api_key: str, api_secret: str, timeout_seconds: int = 15) -> str:
    try:
        response = requests.post(
            AMADEUS_AUTH_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "client_id": api_key,
                "client_secret": api_secret,
            },
            timeout=timeout_seconds,
        )
    except requests.RequestException as request_error:
        raise FlightApiError(f"Failed to obtain Amadeus access token: {request_error}") from request_error

    if response.status_code >= 400:
        raise FlightApiError(f"Amadeus auth returned {response.status_code}: {response.text}")

    access_token = response.json().get("access_token")
    if not access_token:
        raise FlightApiError("Amadeus auth response did not include an access_token")
    return access_token


def find_cheapest_fare(
    access_token: str,
    origin: str,
    destination: str,
    departure_date_from: str,
    departure_date_to: str,
    one_way: bool,
    nonstop_only: bool,
    currency: str,
    duration_range: str = None,
    timeout_seconds: int = 20,
) -> dict:
    params = {
        "origin": origin,
        "destination": destination,
        "departureDate": f"{departure_date_from},{departure_date_to}",
        "oneWay": "true" if one_way else "false",
        "nonStop": "true" if nonstop_only else "false",
        "currencyCode": currency,
    }
    if duration_range:
        params["duration"] = duration_range

    try:
        response = requests.get(
            AMADEUS_FLIGHT_DATES_URL,
            params=params,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=timeout_seconds,
        )
    except requests.RequestException as request_error:
        raise FlightApiError(
            f"Failed to search flight dates for {origin}->{destination}: {request_error}"
        ) from request_error

    if response.status_code >= 400:
        raise FlightApiError(f"Amadeus flight-dates returned {response.status_code}: {response.text}")

    offers = response.json().get("data", [])
    if not offers:
        return None

    cheapest = min(offers, key=lambda offer: float(offer["price"]["total"]))
    return {
        "price": float(cheapest["price"]["total"]),
        "currency": currency,
        "departure_date": cheapest.get("departureDate"),
        "return_date": cheapest.get("returnDate"),
    }
