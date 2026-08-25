import requests


class FetchError(Exception):
    pass


def fetch_html(url: str, timeout_seconds: int = 15) -> str:
    try:
        response = requests.get(url, timeout=timeout_seconds)
    except requests.RequestException as request_error:
        raise FetchError(f"Failed to fetch {url}: {request_error}") from request_error

    if response.status_code != 200:
        raise FetchError(f"Unexpected status code {response.status_code} for {url}")

    return response.text
