"""Tests for v0.5c discover-api endpoint scoring + stub generation.

These tests don't launch a browser — they exercise the heuristic scorer and
the stub generator with synthetic captured-pair data.
"""

from __future__ import annotations

from urllib.parse import urlparse

from deltasci.acquisition.discover_api import (
    _generate_stub,
    _identify_endpoints,
    _is_static_or_tracking,
    _shape_of,
)


def test_static_assets_are_filtered():
    assert _is_static_or_tracking("https://example.com/static/main.js")
    assert _is_static_or_tracking("https://example.com/img/logo.png")
    assert _is_static_or_tracking("https://www.google-analytics.com/g/collect")
    assert not _is_static_or_tracking("https://example.com/api/correlation")


def test_shape_of_handles_nested_json():
    sample = {"locus": "DRB1", "rho": 0.927, "ns": [1, 2, 3]}
    shape = _shape_of(sample)
    assert isinstance(shape, dict)
    assert shape["rho"] == "float"
    assert isinstance(shape["ns"], list)


def test_endpoint_scoring_prefers_same_origin_api_paths():
    pairs = [
        {
            "request": {"url": "https://marco.igen.org.br/api/correlation", "method": "POST", "post_data": '{"a1": "DRB1*15:01"}'},
            "response": {"url": "https://marco.igen.org.br/api/correlation", "status": 200,
                         "body_summary": {"kind": "json", "size_bytes": 800, "shape": {"rho_pooled": "float", "samples": ["int", "...×100"]}}},
            "resource_type": "fetch",
        },
        {
            "request": {"url": "https://cdn.example.com/main.js", "method": "GET"},
            "response": {"url": "https://cdn.example.com/main.js", "status": 200,
                         "body_summary": {"kind": "other", "content_type": "application/javascript", "size_bytes": 50000}},
            "resource_type": "script",
        },
        {
            "request": {"url": "https://www.google-analytics.com/collect", "method": "GET"},
            "response": {"url": "https://www.google-analytics.com/collect", "status": 200,
                         "body_summary": {"kind": "other", "content_type": "image/gif", "size_bytes": 35}},
            "resource_type": "xhr",
        },
    ]
    page_origin = urlparse("https://marco.igen.org.br/")
    endpoints = _identify_endpoints(pairs, page_origin)
    assert len(endpoints) == 1  # static + tracking filtered
    assert endpoints[0]["method"] == "POST"
    assert "/api/correlation" in endpoints[0]["url"]
    assert "same-origin" in endpoints[0]["score_reasons"]


def test_endpoint_dedup_by_method_path():
    """Multiple queries to the same path with different params dedup to one entry."""

    pairs = [
        {
            "request": {"url": "https://example.com/api/q?a=1", "method": "GET"},
            "response": {"url": "https://example.com/api/q?a=1", "status": 200,
                         "body_summary": {"kind": "json", "size_bytes": 500, "shape": {}}},
            "resource_type": "xhr",
        },
        {
            "request": {"url": "https://example.com/api/q?a=2", "method": "GET"},
            "response": {"url": "https://example.com/api/q?a=2", "status": 200,
                         "body_summary": {"kind": "json", "size_bytes": 500, "shape": {}}},
            "resource_type": "xhr",
        },
    ]
    endpoints = _identify_endpoints(pairs, urlparse("https://example.com"))
    assert len(endpoints) == 1


def test_stub_generation_post_with_payload():
    endpoints = [{
        "method": "POST",
        "url": "https://api.example.com/v1/query",
        "request_post_data": '{"locus": "DRB1", "allele1": "*15:01"}',
        "score": 5.0,
        "score_reasons": ["same-origin", "/api/", "POST-with-payload"],
        "response_shape": {},
    }]
    stub = _generate_stub(endpoints, source_url="https://example.com/")
    assert "import requests" in stub
    assert "https://api.example.com" in stub
    assert "/v1/query" in stub
    assert "requests.post" in stub
    assert "locus" in stub  # payload sample preserved


def test_stub_generation_get_with_query():
    endpoints = [{
        "method": "GET",
        "url": "https://api.example.com/data?filter=active",
        "request_post_data": None,
        "score": 4.0,
        "score_reasons": ["same-origin", "/data"],
        "response_shape": {},
    }]
    stub = _generate_stub(endpoints, source_url="https://example.com/")
    assert "requests.get" in stub
    assert "filter=active" in stub  # captured query string surfaced as comment


def test_stub_generation_with_no_endpoints():
    stub = _generate_stub([], source_url="https://example.com/")
    assert "No data-bearing endpoints" in stub
