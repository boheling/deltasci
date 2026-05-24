"""Tiny stdlib-only HTTP helper used by all audit verifiers.

Stays on `urllib` so audit is part of core install with no extra deps.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

USER_AGENT = "deltasci/0.1.2 (https://github.com/deltasci/deltasci) audit-pillar"


class HTTPError(Exception):
    pass


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
    req = urllib.request.Request(url, headers=merged_headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
    except urllib.error.HTTPError as exc:
        raise HTTPError(f"{exc.code} {exc.reason} for {url}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise HTTPError(f"network error for {url}: {exc}") from exc

    try:
        return json.loads(data.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise HTTPError(f"invalid JSON from {url}: {exc}") from exc


def get_text(url: str, timeout: float = 10.0, params: dict[str, str] | None = None) -> str:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raise HTTPError(f"{exc.code} {exc.reason} for {url}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise HTTPError(f"network error for {url}: {exc}") from exc
