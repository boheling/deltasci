"""Unit tests for the MARCo stratified-pull module.

All HTTP is mocked. Live-API smoke tests would go behind a `pytest -m live`
marker; here we exercise the wire-format building, min-N gate logic, the
disk-backed cache, and the row-from-payload mapping.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from deltasci.acquisition.marco_strata import (
    BY_SEX,
    OVERALL,
    SENSITIZATION_ROUTES,
    MinNGate,
    Stratum,
    StratumCache,
    StratumRow,
    _build_body,
    _row_from_payload,
    fetch_analyze,
    pull_stratified,
)


# --- Wire format -------------------------------------------------------------


def test_build_body_uses_plural_filter_keys_with_null_defaults():
    body = _build_body("DRB1*01:01", "DRB1*15:01", OVERALL)
    # All filter keys present, all None
    for k in ("sex", "transplants", "transfusions", "pregnancies"):
        assert k in body
        assert body[k] is None
    # Required non-filter fields
    assert body["allele_1"] == "DRB1*01:01"
    assert body["allele_2"] == "DRB1*15:01"
    assert body["mfi_positive_cutoff"] == 1500
    assert body["mfi_negative_cutoff"] == 300
    # Singular forms must NOT be present (they are silently ignored by the API).
    assert "sex_filter" not in body
    assert "transplant" not in body
    assert "transfusion" not in body
    assert "pregnancy" not in body


def test_build_body_applies_only_specified_filters():
    s = Stratum("female_parous", {"sex": "Female", "pregnancies": ">= 1"})
    body = _build_body("A*01:01", "A*01:02", s)
    assert body["sex"] == "Female"
    assert body["pregnancies"] == ">= 1"
    assert body["transplants"] is None
    assert body["transfusions"] is None


# --- Min-N gate --------------------------------------------------------------


def test_min_n_gate_passes_when_all_thresholds_clear():
    g = MinNGate(min_total_samples=100, min_a1_positives=5, min_a2_positives=5)
    keep, reason = g.evaluate(total=200, a1_pos=20, a2_pos=15)
    assert keep is True and reason == ""


def test_min_n_gate_drops_on_total_below_threshold():
    g = MinNGate(min_total_samples=100)
    keep, reason = g.evaluate(total=50, a1_pos=20, a2_pos=20)
    assert keep is False
    assert "n_total=50" in reason and "100" in reason


def test_min_n_gate_drops_on_either_allele_starvation():
    g = MinNGate(min_a1_positives=5, min_a2_positives=5)
    keep, _ = g.evaluate(total=500, a1_pos=2, a2_pos=20)
    assert keep is False
    keep, _ = g.evaluate(total=500, a1_pos=20, a2_pos=3)
    assert keep is False


# --- Disk cache --------------------------------------------------------------


def test_disk_cache_round_trip(tmp_path):
    cache = StratumCache(tmp_path / "cache")
    body = {"allele_1": "A", "allele_2": "B", "sex": "Female", "transplants": None}
    payload = {"success": True, "result": {"correlation": 0.5}}
    assert cache.get(body) is None
    cache.set(body, payload)
    assert cache.get(body) == payload


def test_disk_cache_keys_distinguish_strata(tmp_path):
    cache = StratumCache(tmp_path / "cache")
    body_f = {"allele_1": "A", "allele_2": "B", "sex": "Female"}
    body_m = {"allele_1": "A", "allele_2": "B", "sex": "Male"}
    cache.set(body_f, {"success": True, "tag": "F"})
    cache.set(body_m, {"success": True, "tag": "M"})
    assert cache.get(body_f)["tag"] == "F"
    assert cache.get(body_m)["tag"] == "M"


# --- fetch_analyze HTTP path --------------------------------------------------


def _fake_payload(rho=0.5, total=300, a1_pos=20, a2_pos=18):
    return {
        "success": True,
        "result": {
            "allele_1": "A*01:01", "allele_2": "A*01:02",
            "total_samples": total,
            "allele_1_positive_count": a1_pos,
            "allele_2_positive_count": a2_pos,
            "correlation": rho,
            "correlation_type": "Spearman",
        },
        "error": None,
    }


def test_fetch_analyze_uses_cache_on_second_call(tmp_path):
    cache = StratumCache(tmp_path / "cache")
    payload = _fake_payload()
    with patch("deltasci.acquisition.marco_strata._post_json", return_value=payload) as mock_post:
        first = fetch_analyze("A", "B", OVERALL, cache=cache)
        second = fetch_analyze("A", "B", OVERALL, cache=cache)
    assert first == payload and second == payload
    assert mock_post.call_count == 1, "second call should hit cache"


def test_fetch_analyze_does_not_cache_failures(tmp_path):
    cache = StratumCache(tmp_path / "cache")
    failure = {"success": False, "result": {}, "error": "boom"}
    with patch("deltasci.acquisition.marco_strata._post_json", return_value=failure) as mock_post:
        fetch_analyze("A", "B", OVERALL, cache=cache)
        fetch_analyze("A", "B", OVERALL, cache=cache)
    assert mock_post.call_count == 2, "failed responses must not be cached"


# --- Row-building -------------------------------------------------------------


def test_row_from_payload_retains_when_gate_clears():
    payload = _fake_payload(rho=0.62, total=500, a1_pos=40, a2_pos=35)
    row = _row_from_payload("A", "B", OVERALL, payload, MinNGate())
    assert row.retained is True and row.drop_reason == ""
    assert row.correlation == pytest.approx(0.62)
    assert row.n_total == 500


def test_row_from_payload_flags_dropped_with_reason():
    payload = _fake_payload(rho=0.62, total=20, a1_pos=2, a2_pos=2)
    row = _row_from_payload("A", "B", OVERALL, payload, MinNGate())
    assert row.retained is False
    assert "n_total=20" in row.drop_reason


def test_row_from_payload_handles_api_error():
    failure = {"success": False, "result": {}, "error": "rate-limited"}
    row = _row_from_payload("A", "B", OVERALL, failure, MinNGate())
    assert row.retained is False
    assert "rate-limited" in row.drop_reason
    assert row.correlation is None


# --- End-to-end stratified pull ----------------------------------------------


def test_pull_stratified_emits_one_row_per_pair_x_stratum(tmp_path):
    cache = StratumCache(tmp_path / "cache")

    def _fake(body, timeout=60.0):  # noqa: ARG001
        # Different ρ per stratum so we can tell rows apart
        rho = 0.7 if body["sex"] == "Female" else (0.6 if body["sex"] == "Male" else 0.5)
        return _fake_payload(rho=rho, total=500, a1_pos=30, a2_pos=30)

    with patch("deltasci.acquisition.marco_strata._post_json", side_effect=_fake):
        rows = pull_stratified(
            pairs=[("A*01:01", "A*01:02"), ("DRB1*01:01", "DRB1*15:01")],
            strata=(OVERALL, *BY_SEX),
            cache=cache, workers=2, progress_every=0,
        )

    assert len(rows) == 2 * 3
    by_pair = {(r.allele_1, r.allele_2, r.stratum): r for r in rows}
    assert by_pair[("A*01:01", "A*01:02", "overall")].correlation == pytest.approx(0.5)
    assert by_pair[("A*01:01", "A*01:02", "female")].correlation == pytest.approx(0.7)
    assert by_pair[("A*01:01", "A*01:02", "male")].correlation == pytest.approx(0.6)
    # All retained
    assert all(r.retained for r in rows)


def test_pull_stratified_keeps_underpowered_rows_with_flag(tmp_path):
    cache = StratumCache(tmp_path / "cache")

    def _fake(body, timeout=60.0):  # noqa: ARG001
        # Male × everything → tiny cohort; everything else fine
        if body.get("sex") == "Male":
            return _fake_payload(rho=0.4, total=50, a1_pos=2, a2_pos=2)
        return _fake_payload(rho=0.6, total=500, a1_pos=30, a2_pos=30)

    with patch("deltasci.acquisition.marco_strata._post_json", side_effect=_fake):
        rows = pull_stratified(
            pairs=[("A", "B")], strata=BY_SEX, cache=cache, workers=1, progress_every=0,
        )
    by_label = {r.stratum: r for r in rows}
    assert by_label["female"].retained is True
    assert by_label["male"].retained is False
    assert "n_total=50" in by_label["male"].drop_reason


def test_pull_stratified_survives_per_call_exceptions(tmp_path):
    cache = StratumCache(tmp_path / "cache")

    def _fake(body, timeout=60.0):  # noqa: ARG001
        if body.get("sex") == "Male":
            raise RuntimeError("net broke")
        return _fake_payload()

    with patch("deltasci.acquisition.marco_strata._post_json", side_effect=_fake):
        rows = pull_stratified(
            pairs=[("A", "B")], strata=BY_SEX, cache=cache, workers=1, progress_every=0,
        )
    by_label = {r.stratum: r for r in rows}
    assert by_label["female"].retained is True
    assert by_label["male"].retained is False
    assert "exception" in by_label["male"].drop_reason or "net broke" in by_label["male"].drop_reason
