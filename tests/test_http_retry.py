"""Retry/backoff behavior for the audit HTTP helper (no real network or sleeps)."""

from __future__ import annotations

import urllib.error

import pytest

import deltasci.audit.http as http


class _Resp:
    def __init__(self, data: bytes) -> None:
        self._d = data

    def read(self) -> bytes:
        return self._d

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(http.time, "sleep", lambda _s: None)


def test_retries_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def fake_urlopen(req, timeout=10.0):
        calls["n"] += 1
        if calls["n"] == 1:
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", {}, None)
        return _Resp(b'{"ok": true}')

    monkeypatch.setattr(http.urllib.request, "urlopen", fake_urlopen)
    assert http.get_json("https://x.test/") == {"ok": True}
    assert calls["n"] == 2  # one 429, then success


def test_non_retryable_status_raises_immediately(monkeypatch):
    calls = {"n": 0}

    def fake_urlopen(req, timeout=10.0):
        calls["n"] += 1
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr(http.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(http.HTTPError):
        http.get_text("https://x.test/")
    assert calls["n"] == 1  # 404 is not retried


def test_gives_up_after_max_retries(monkeypatch):
    calls = {"n": 0}

    def fake_urlopen(req, timeout=10.0):
        calls["n"] += 1
        raise urllib.error.HTTPError(req.full_url, 503, "Service Unavailable", {}, None)

    monkeypatch.setattr(http.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(http.HTTPError):
        http.get_json("https://x.test/")
    assert calls["n"] == http.DEFAULT_RETRIES + 1
