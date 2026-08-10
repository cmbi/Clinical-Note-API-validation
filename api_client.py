# api_client.py
# Shared helper for API GET requests.

import time
import requests

from config import REQUEST_TIMEOUT_SECONDS, USER_AGENT


_last_request_time_by_host = {}


def api_get_json(url, params=None, headers=None, min_interval_seconds=0):
    """
    Send a GET request and return the JSON response.

    Returns:
        A Python dictionary/list if the request succeeds and the response is JSON.
        None if the request fails, the status code is not 200, or JSON parsing fails.
    """
    _respect_rate_limit(url, min_interval_seconds)

    request_headers = {
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }

    if headers is not None:
        request_headers.update(headers)

    try:
        response = requests.get(
            url,
            params=params,
            headers=request_headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as error:
        print(f"Request error for {url}: {error}")
        return None

    if response.status_code != 200:
        print(f"API error for {response.url}: HTTP {response.status_code}")
        return None

    try:
        return response.json()
    except ValueError:
        print(f"Invalid JSON response from {response.url}")
        return None


def _respect_rate_limit(url, min_interval_seconds):
    """Simple rate limiter per host."""
    if min_interval_seconds <= 0:
        return

    host = url.split("/")[2] if "://" in url else "default"
    last_request_time = _last_request_time_by_host.get(host)
    now = time.monotonic()

    if last_request_time is not None:
        wait_time = min_interval_seconds - (now - last_request_time)
        if wait_time > 0:
            time.sleep(wait_time)

    _last_request_time_by_host[host] = time.monotonic()
