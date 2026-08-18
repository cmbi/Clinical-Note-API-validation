import time
import requests

from config import REQUEST_TIMEOUT_SECONDS, MAX_RETRIES

# Reuse connections across all requests
session = requests.Session()

RETRYABLE_STATUS_CODES = {500, 502, 503, 504}

last_request_time_by_host = {}


def api_get_json(url, params=None, headers=None, min_interval_seconds=0):
    """
    Send a GET request and return the JSON response.

    Returns:
        A Python dictionary/list if the request succeeds and the response is JSON.
        None: if the request fails, the status code is not 200, or JSON parsing fails.
    """

    request_headers = {
        "Accept": "application/json"
    }

    if headers is not None:
        request_headers.update(headers)

    for attempt in range(MAX_RETRIES + 1):
        respect_rate_limit(url, min_interval_seconds)        

        try:
            response = session.get(
                url,
                params=params,
                headers=request_headers,
                timeout=REQUEST_TIMEOUT_SECONDS
            )
        except requests.exceptions.ReadTimeout:
            print(f"Read timeout for {response.url} (attempt {attempt + 1}/{MAX_RETRIES + 1})")
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
                continue
            return None

        except requests.exceptions.ConnectTimeout:
            print(f"Connect timeout for {response.url} (attempt {attempt + 1}/{MAX_RETRIES + 1})")
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
                continue
            return None

        except requests.RequestException as error:
            print(f"Request error for {response.url}: {error}")
            return None

        if response.status_code == 200:
            try:
                return response.json()
            except ValueError:
                print(f"Invalid JSON response from {response.url}")
                return None
        if response.status_code in RETRYABLE_STATUS_CODES:
            print(
            f"API error for {response.url}: "
            f"HTTP {response.status_code} "
            f"(attempt {attempt + 1}/{MAX_RETRIES + 1})"
            )

            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
                continue
            return None

        print(f"API error for {response.url}: HTTP {response.status_code}")
        return None
    return None


def respect_rate_limit(url, min_interval_seconds):
    """Simple rate limiter per host."""
    if min_interval_seconds <= 0:
        return

    host = url.split("/")[2] if "://" in url else "default"
    last_request_time = last_request_time_by_host.get(host)
    now = time.monotonic()

    if last_request_time is not None:
        wait_time = min_interval_seconds - (now - last_request_time)
        if wait_time > 0:
            time.sleep(wait_time)

    last_request_time_by_host[host] = time.monotonic()
