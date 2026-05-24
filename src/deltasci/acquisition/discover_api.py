"""Headed-Playwright API discovery.

Workflow:
  1. Launch a real Chromium window at the URL
  2. The user interacts (click queries, change filters) — the way they would
     in browser DevTools while reverse-engineering an API
  3. Every XHR / fetch request + response is captured to JSON
  4. After timeout or user closes the window, we rank the captured endpoints
     by "looks like a data API" heuristics and emit a Python `requests` stub

No LLM call is required — endpoint identification is heuristic-only in v0.5.0
(deferred LLM-driven analysis to v0.5.1 if heuristics prove insufficient).
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


def discover_api(
    *,
    url: str,
    describe: str = "",
    out_dir: Path | None = None,
    timeout_seconds: int = 300,
) -> dict:
    """Launch Playwright, capture network, identify endpoints, write stubs.

    Returns a result dict with: out_dir, request_count, xhr_count, endpoints.
    Raises RuntimeError if Playwright isn't installed (caller surfaces the message).
    """

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - environment-dependent
        raise RuntimeError(
            "Playwright not installed. Install with:\n"
            "  pip install 'deltasci[discover]'\n"
            "  playwright install chromium"
        ) from exc

    if out_dir is None:
        out_dir = Path("deltasci-discover") / datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    captured: list[dict] = []

    print(f"deltasci discover-api → launching headed Chromium at {url}")
    print(f"  output dir: {out_dir.resolve()}")
    print(f"  timeout:    {timeout_seconds}s (Ctrl-C in this terminal to capture earlier)")
    if describe:
        print(f"  goal:       {describe}")
    print()
    print("Interact with the page in the browser window:")
    print("  - Click queries / change filters / load views you'd use programmatically")
    print("  - Each XHR/fetch is being recorded")
    print("  - Close the browser window OR wait for the timeout to finish capture")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.on("request", lambda r: _on_request(r, captured))
        page.on("response", lambda r: _on_response(r, captured))

        try:
            page.goto(url, timeout=30_000)
        except Exception as exc:  # noqa: BLE001
            browser.close()
            raise RuntimeError(f"failed to load {url}: {exc}") from exc

        try:
            # Wait either for the user to close the window or for the timeout.
            page.wait_for_event("close", timeout=timeout_seconds * 1000)
        except Exception:
            # Timeout or user-closed; either way proceed to analysis.
            pass
        finally:
            try:
                browser.close()
            except Exception:
                pass

    # Pair requests with responses
    pairs = _pair_requests_with_responses(captured)

    capture_path = out_dir / "capture.json"
    capture_path.write_text(
        json.dumps({"url": url, "describe": describe, "pairs": pairs}, indent=2),
        encoding="utf-8",
    )

    endpoints = _identify_endpoints(pairs, page_origin=urlparse(url))
    endpoints_path = out_dir / "endpoints.json"
    endpoints_path.write_text(json.dumps(endpoints, indent=2), encoding="utf-8")

    stub_text = _generate_stub(endpoints, source_url=url)
    (out_dir / "api_stub.py").write_text(stub_text, encoding="utf-8")

    return {
        "out_dir": str(out_dir),
        "request_count": len([p for p in pairs if p.get("request")]),
        "xhr_count": len([p for p in pairs if p.get("resource_type") in ("xhr", "fetch")]),
        "endpoints": endpoints,
    }


# ---- Capture --------------------------------------------------------------


def _on_request(request, captured: list[dict]) -> None:
    try:
        post_data = request.post_data
    except Exception:
        post_data = None
    captured.append({
        "phase": "request",
        "id": id(request),  # rough pairing key
        "url": request.url,
        "method": request.method,
        "resource_type": request.resource_type,
        "headers": dict(request.headers) if request.headers else {},
        "post_data": post_data,
        "timestamp": datetime.now().isoformat(),
    })


def _on_response(response, captured: list[dict]) -> None:
    try:
        text = response.text() if response.status < 400 else None
    except Exception:
        text = None
    body_summary = None
    if text:
        body_summary = _summarize_body(text, response.headers.get("content-type", ""))
    captured.append({
        "phase": "response",
        "id": id(response.request),
        "url": response.url,
        "status": response.status,
        "headers": dict(response.headers) if response.headers else {},
        "body_summary": body_summary,
        "body_text_preview": (text or "")[:2000] if text else None,
        "timestamp": datetime.now().isoformat(),
    })


def _summarize_body(text: str, content_type: str) -> dict:
    """Best-effort body shape: parse JSON, otherwise show length + content-type."""

    if "json" in content_type.lower() or text.strip().startswith(("{", "[")):
        try:
            data = json.loads(text)
            return {"kind": "json", "shape": _shape_of(data), "size_bytes": len(text)}
        except json.JSONDecodeError:
            pass
    return {"kind": "other", "content_type": content_type, "size_bytes": len(text)}


def _shape_of(value, depth: int = 0) -> dict | str:
    """Recursive type-shape descriptor (non-recursive for primitives, depth-limited)."""

    if depth > 4:
        return f"<{type(value).__name__}@truncated>"
    if isinstance(value, dict):
        return {k: _shape_of(v, depth + 1) for k, v in list(value.items())[:20]}
    if isinstance(value, list):
        if not value:
            return "list[]"
        return [_shape_of(value[0], depth + 1), f"...×{len(value)}"]
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return type(value).__name__
    if isinstance(value, str):
        if len(value) > 80:
            return f"str(len={len(value)})"
        return f"str({value[:60]!r})"
    if value is None:
        return "null"
    return type(value).__name__


def _pair_requests_with_responses(captured: list[dict]) -> list[dict]:
    """Stitch each request to its matching response by `id`."""

    by_id: dict[int, dict] = {}
    for evt in captured:
        slot = by_id.setdefault(evt["id"], {})
        if evt["phase"] == "request":
            slot["request"] = {k: v for k, v in evt.items() if k != "phase"}
            slot["resource_type"] = evt.get("resource_type")
        else:
            slot["response"] = {k: v for k, v in evt.items() if k != "phase"}
    return list(by_id.values())


# ---- Endpoint identification ---------------------------------------------


# Filter out: static assets, analytics, fonts, images, sourcemaps
_STATIC_EXTS = {".js", ".css", ".woff", ".woff2", ".ttf", ".otf", ".png", ".jpg",
                ".jpeg", ".gif", ".svg", ".ico", ".map", ".html", ".webmanifest"}
_TRACKING_HOSTS = ("google-analytics.com", "googletagmanager.com", "doubleclick.net",
                    "facebook.net", "facebook.com", "hotjar.com", "segment.io",
                    "datadog", "sentry.io", "cloudflareinsights")


def _identify_endpoints(pairs: list[dict], page_origin) -> list[dict]:
    """Heuristic ranking of captured pairs by "looks like a data API"."""

    candidates: list[dict] = []
    for p in pairs:
        req = p.get("request", {})
        resp = p.get("response", {})
        url = req.get("url") or resp.get("url") or ""
        if not url:
            continue
        if _is_static_or_tracking(url):
            continue
        body = resp.get("body_summary") or {}
        if body.get("kind") != "json":
            # Allow non-JSON XHR (e.g., XML, text/plain) but rank lower.
            if p.get("resource_type") not in ("xhr", "fetch"):
                continue

        score, reasons = _score_endpoint(req, resp, body, page_origin)
        candidates.append({
            "method": req.get("method", "?"),
            "url": url,
            "resource_type": p.get("resource_type"),
            "status": resp.get("status"),
            "request_post_data": req.get("post_data"),
            "response_shape": body.get("shape") if body.get("kind") == "json" else None,
            "response_size_bytes": body.get("size_bytes"),
            "score": score,
            "score_reasons": reasons,
        })

    candidates.sort(key=lambda c: c["score"], reverse=True)
    # Group near-duplicates (same path, different querystring) under a single best entry
    seen_paths: set[str] = set()
    deduped: list[dict] = []
    for c in candidates:
        path = urlparse(c["url"]).path
        method_path = f"{c['method']} {path}"
        if method_path in seen_paths:
            continue
        seen_paths.add(method_path)
        deduped.append(c)
    return deduped[:20]


def _is_static_or_tracking(url: str) -> bool:
    parsed = urlparse(url)
    if any(host in parsed.netloc for host in _TRACKING_HOSTS):
        return True
    path = parsed.path.lower()
    if any(path.endswith(ext) for ext in _STATIC_EXTS):
        return True
    return False


def _score_endpoint(req: dict, resp: dict, body: dict, page_origin) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []

    # Same-origin → likely backend API (cross-origin hits are often CDN/3p)
    parsed = urlparse(req.get("url", ""))
    if page_origin.netloc and parsed.netloc == page_origin.netloc:
        score += 2.0
        reasons.append("same-origin")
    elif parsed.netloc and "api" in parsed.netloc:
        score += 1.5
        reasons.append("subdomain-named-api")

    # Path hints — endpoints with /api/, /v1/, /query/, /search/ are stronger
    path = parsed.path.lower()
    for token, weight in (("/api/", 3.0), ("/v1/", 1.5), ("/v2/", 1.5),
                          ("/query", 2.0), ("/search", 1.5), ("/data", 1.5),
                          ("/correlation", 2.5), ("/pair", 1.5)):
        if token in path:
            score += weight
            reasons.append(f"path:{token}")

    # JSON response with non-trivial size
    if body.get("kind") == "json":
        size = body.get("size_bytes", 0)
        if size > 200:
            score += 1.5
            reasons.append(f"json-{size}B")
        # Response shape with top-level dict containing arrays = data-bearing
        shape = body.get("shape")
        if isinstance(shape, dict):
            for v in shape.values():
                if isinstance(v, list):
                    score += 1.0
                    reasons.append("response-has-array")
                    break

    # POST with payload → query-style API
    if req.get("method") == "POST" and req.get("post_data"):
        score += 1.5
        reasons.append("POST-with-payload")

    # Response status 200
    if resp.get("status") == 200:
        score += 0.5
        reasons.append("200-OK")
    elif (resp.get("status") or 0) >= 400:
        score -= 2.0
        reasons.append("error-status")

    return score, reasons


# ---- Stub generation -----------------------------------------------------


def _generate_stub(endpoints: list[dict], source_url: str) -> str:
    """Emit a Python stub showing how to call the top-ranked endpoint."""

    if not endpoints:
        return _empty_stub(source_url)

    top = endpoints[0]
    method = top["method"]
    url = top["url"]
    post_data = top.get("request_post_data")
    parsed = urlparse(url)
    scheme_host = f"{parsed.scheme}://{parsed.netloc}"
    path = parsed.path

    lines = [
        '"""Auto-generated API stub from deltasci discover-api.',
        f'Source page: {source_url}',
        f'Identified endpoint: {method} {url}',
        f'Score: {top["score"]:.2f}  ({", ".join(top["score_reasons"])})',
        '',
        'NOTE: this is a starting point. Verify the parameter names + types',
        'against endpoints.json and the live API before using at scale.',
        '"""',
        '',
        'import requests',
        '',
        f'BASE_URL = {scheme_host!r}',
        f'ENDPOINT_PATH = {path!r}',
        '',
    ]

    if method == "POST" and post_data:
        # Attempt to infer JSON payload shape
        try:
            payload_obj = json.loads(post_data)
            lines.extend([
                'def call_api(**params) -> dict:',
                '    """Call the discovered POST endpoint.',
                '',
                '    Sample payload structure (as captured):',
            ])
            for line in json.dumps(payload_obj, indent=4).splitlines():
                lines.append(f'    {line}')
            lines.extend([
                '    """',
                '    payload = {**' + json.dumps(payload_obj) + ', **params}',
                f'    r = requests.post(BASE_URL + ENDPOINT_PATH, json=payload, timeout=30)',
                '    r.raise_for_status()',
                '    return r.json()',
            ])
        except json.JSONDecodeError:
            lines.extend([
                'def call_api(payload: str) -> dict:',
                '    """Call the discovered POST endpoint."""',
                f'    r = requests.post(BASE_URL + ENDPOINT_PATH, data=payload, timeout=30)',
                '    r.raise_for_status()',
                '    return r.json()',
            ])
    else:
        # GET (with query params extracted from the URL)
        query = parsed.query
        lines.extend([
            'def call_api(**params) -> dict:',
            '    """Call the discovered GET endpoint."""',
        ])
        if query:
            lines.append(f'    # Sample query string from capture: {query!r}')
        lines.extend([
            '    r = requests.get(BASE_URL + ENDPOINT_PATH, params=params, timeout=30)',
            '    r.raise_for_status()',
            '    return r.json()',
        ])

    lines.extend([
        '',
        '',
        'if __name__ == "__main__":',
        '    # Sanity check — confirm the endpoint resolves and returns JSON.',
        '    sample = call_api()' if method != 'POST' else '    sample = call_api()',
        '    import json as _json',
        '    print(_json.dumps(sample, indent=2)[:1000])',
        '',
        '# --- Other candidate endpoints (from endpoints.json) ---',
    ])
    for e in endpoints[1:6]:
        lines.append(f'#   {e["score"]:.2f}  {e["method"]} {e["url"]}')

    return "\n".join(lines) + "\n"


def _empty_stub(source_url: str) -> str:
    return (
        '"""Auto-generated API stub from deltasci discover-api.\n\n'
        f'Source: {source_url}\n\n'
        'No data-bearing endpoints were identified during the capture window.\n'
        'Possibilities:\n'
        '  - The page renders entirely on the server (no XHR/fetch to capture)\n'
        '  - You did not interact with the page in a way that triggered data calls\n'
        '  - The data layer uses WebSockets (not yet captured by this v0.5.0 implementation)\n'
        '"""\n'
    )
