"""Tiny stdlib-only HTTP helper used by all audit verifiers.

Stays on `urllib` so audit is part of core install with no extra deps.

Verifiers run concurrently and several share rate-limited hosts (NCBI E-utilities
allows only ~3 req/s without an API key), so a burst easily trips HTTP 429. We retry
transient failures (429 + 5xx + network errors) with exponential backoff so a citation
is reported `skipped` only when it's genuinely unreachable, not merely rate-limited.
"""

from __future__ import annotations

import json
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

USER_AGENT = "deltasci/0.9.0 (https://github.com/boheling/deltasci) audit-pillar"

RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
DEFAULT_RETRIES = 3


class HTTPError(Exception):
    pass


def _backoff_seconds(attempt: int) -> float:
    # 0.6s, 1.2s, 2.4s … plus jitter to de-synchronize concurrent workers.
    return 0.6 * (2**attempt) + random.uniform(0.0, 0.4)


def _fetch_bytes(url: str, timeout: float, headers: dict[str, str], retries: int = DEFAULT_RETRIES) -> bytes:
    last: HTTPError | None = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            last = HTTPError(f"{exc.code} {exc.reason} for {url}")
            retryable = exc.code in RETRY_STATUSES
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = HTTPError(f"network error for {url}: {exc}")
            retryable = True
        if retryable and attempt < retries:
            time.sleep(_backoff_seconds(attempt))
            continue
        assert last is not None
        raise last
    assert last is not None  # pragma: no cover - loop always returns or raises
    raise last


def get_json(
    url: str,
    timeout: float = 10.0,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    merged_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        merged_headers.update(headers)
    data = _fetch_bytes(url, timeout, merged_headers)
    try:
        return json.loads(data.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise HTTPError(f"invalid JSON from {url}: {exc}") from exc


def get_text(
    url: str,
    timeout: float = 10.0,
    params: dict[str, str] | None = None,
    retries: int = DEFAULT_RETRIES,
) -> str:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    return _fetch_bytes(url, timeout, {"User-Agent": USER_AGENT}, retries=retries).decode("utf-8", errors="replace")
