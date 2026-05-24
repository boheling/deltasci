"""MARCo stratified pull — per-pair pulls against /api/analyze with patient-
level demographic filters (sex / pregnancies / transplants / transfusions).

The bulk `/api/correlation-matrix` endpoint silently ignores demographic
filters; only `/api/analyze` honors them. So a stratified pull is one HTTP
call per (pair, stratum). With ~1,800 pairs and ~5-7 strata, that's
~10-12k calls — slow without caching, fast with.

Design choices baked in:
  - **Disk-backed cache** keyed by (allele_1, allele_2, sex, transplants,
    transfusions, pregnancies). Re-runs are O(missing) calls.
  - **Min-N gate** (the 'too small for significant conclusion' guard) is a
    first-class output, NOT silent dropping. The returned DataFrame keeps
    underpowered rows tagged `retained=False` so you can audit the gate.
  - **Concurrent execution** via ThreadPoolExecutor; default 4 workers to
    stay polite to a public Brazilian endpoint.
  - **Wire format** verified against the live UI on 2026-05-06: param names
    are *plural* (transplants, transfusions, pregnancies). Default values
    on omitted filters are `null`, not the string "All".
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.request as _urlreq
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence


MARCO_API_ANALYZE = "https://marco.igen.org.br/api/analyze"


# --- Stratum spec ------------------------------------------------------------


# Wire-level filter keys MARCo accepts. Plural names matter (we got bitten
# guessing singular forms). Each value is either None (filter not applied)
# or a string from the corresponding `/api/options` list.
FILTER_KEYS = ("sex", "transplants", "transfusions", "pregnancies")


@dataclass(frozen=True)
class Stratum:
    """One named demographic slice. `filters` carries only the non-default
    fields; the rest are `null` on the wire."""

    label: str
    filters: dict[str, str] = field(default_factory=dict)

    def wire_filters(self) -> dict[str, str | None]:
        return {k: self.filters.get(k) for k in FILTER_KEYS}


# Pre-built stratum sets users can grab off the shelf.

OVERALL = Stratum("overall", {})

BY_SEX = (
    Stratum("female", {"sex": "Female"}),
    Stratum("male",   {"sex": "Male"}),
)

BY_TRANSPLANT_HISTORY = (
    Stratum("primary",       {"transplants": "0"}),
    Stratum("retransplant",  {"transplants": ">= 1"}),
)

BY_PARITY_FEMALE = (
    Stratum("female_nullipara", {"sex": "Female", "pregnancies": "0"}),
    Stratum("female_parous",    {"sex": "Female", "pregnancies": ">= 1"}),
)

BY_TRANSFUSION_LOAD = (
    Stratum("transfusion_naive",     {"transfusions": "0"}),
    Stratum("transfusion_lightly",   {"transfusions": "1-5"}),
    Stratum("transfusion_heavy",     {"transfusions": ">5"}),
)

# Default set used by the demo CLI. Designed to surface biggest-effect
# splits (sex × parity × transplant history) without exploding the API call
# count past ~5x the pair count.
SENSITIZATION_ROUTES: tuple[Stratum, ...] = (
    OVERALL,
    Stratum("female_nullipara",  {"sex": "Female", "pregnancies": "0"}),
    Stratum("female_parous",     {"sex": "Female", "pregnancies": ">= 1"}),
    Stratum("male_primary",      {"sex": "Male", "transplants": "0"}),
    Stratum("male_retransplant", {"sex": "Male", "transplants": ">= 1"}),
)


# --- Min-N gate --------------------------------------------------------------


@dataclass
class MinNGate:
    """Statistical-power guard. A stratum is `retained` only when ALL three
    counts clear the threshold; otherwise it is kept in the output but
    flagged `retained=False` with a `drop_reason`.

    Defaults are conservative: Spearman ρ stability research (e.g.,
    Bonett & Wright 2000) suggests n≥30 for narrow CIs; we use 100. For
    cross-reactivity to be meaningful we also want each allele to have at
    least 5 positive samples.
    """

    min_total_samples: int = 100
    min_a1_positives: int = 5
    min_a2_positives: int = 5

    def evaluate(self, total: int, a1_pos: int, a2_pos: int) -> tuple[bool, str]:
        if total < self.min_total_samples:
            return False, f"n_total={total} < {self.min_total_samples}"
        if a1_pos < self.min_a1_positives:
            return False, f"a1_pos={a1_pos} < {self.min_a1_positives}"
        if a2_pos < self.min_a2_positives:
            return False, f"a2_pos={a2_pos} < {self.min_a2_positives}"
        return True, ""


# --- Disk-backed cache -------------------------------------------------------


class StratumCache:
    """Tiny disk-backed JSON cache. One file per request, sharded by hash so
    we don't blow up a directory listing past a few thousand entries."""

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _key_path(self, body: dict) -> Path:
        h = hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        bucket = self.root / h[:2]
        bucket.mkdir(parents=True, exist_ok=True)
        return bucket / f"{h}.json"

    def get(self, body: dict) -> dict | None:
        p = self._key_path(body)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — corrupt cache file; ignore
            return None

    def set(self, body: dict, payload: dict) -> None:
        self._key_path(body).write_text(json.dumps(payload), encoding="utf-8")


# --- HTTP --------------------------------------------------------------------


def _build_body(allele_1: str, allele_2: str, stratum: Stratum,
                mfi_positive_cutoff: int = 1500,
                mfi_negative_cutoff: int = 300) -> dict:
    body = {
        "manufacturer": None, "lot": None, "lots": [], "kits": [],
        "mfi_positive_cutoff": mfi_positive_cutoff,
        "mfi_negative_cutoff": mfi_negative_cutoff,
        "allele_1": allele_1, "allele_2": allele_2,
    }
    body.update(stratum.wire_filters())
    return body


def _post_json(body: dict, *, timeout: float = 60.0) -> dict:
    req = _urlreq.Request(
        MARCO_API_ANALYZE, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "deltasci/marco_strata"},
        method="POST",
    )
    with _urlreq.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def fetch_analyze(
    allele_1: str, allele_2: str, stratum: Stratum,
    *,
    cache: StratumCache | None = None,
    timeout: float = 60.0,
) -> dict:
    """One HTTP call (or cache hit). Returns the raw `/api/analyze` payload."""
    body = _build_body(allele_1, allele_2, stratum)
    if cache is not None:
        cached = cache.get(body)
        if cached is not None:
            return cached
    payload = _post_json(body, timeout=timeout)
    if cache is not None and payload.get("success"):
        cache.set(body, payload)
    return payload


# --- Stratified pull ---------------------------------------------------------


@dataclass
class StratumRow:
    allele_1: str
    allele_2: str
    stratum: str
    correlation: float | None
    correlation_type: str
    n_total: int
    n_a1_positive: int
    n_a2_positive: int
    retained: bool
    drop_reason: str = ""

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def _row_from_payload(allele_1: str, allele_2: str, stratum: Stratum,
                       payload: dict, gate: MinNGate) -> StratumRow:
    if not payload.get("success"):
        return StratumRow(
            allele_1=allele_1, allele_2=allele_2, stratum=stratum.label,
            correlation=None, correlation_type="",
            n_total=0, n_a1_positive=0, n_a2_positive=0,
            retained=False, drop_reason=f"api_error: {payload.get('error', 'unknown')}",
        )
    res = payload.get("result") or {}
    n_total = int(res.get("total_samples") or 0)
    a1_pos = int(res.get("allele_1_positive_count") or 0)
    a2_pos = int(res.get("allele_2_positive_count") or 0)
    keep, reason = gate.evaluate(n_total, a1_pos, a2_pos)
    rho = res.get("correlation")
    return StratumRow(
        allele_1=allele_1, allele_2=allele_2, stratum=stratum.label,
        correlation=float(rho) if rho is not None else None,
        correlation_type=str(res.get("correlation_type") or ""),
        n_total=n_total, n_a1_positive=a1_pos, n_a2_positive=a2_pos,
        retained=keep, drop_reason=reason,
    )


def pull_stratified(
    pairs: Sequence[tuple[str, str]],
    strata: Sequence[Stratum] = SENSITIZATION_ROUTES,
    *,
    gate: MinNGate | None = None,
    cache: StratumCache | None = None,
    workers: int = 4,
    request_throttle_seconds: float = 0.0,
    progress_every: int = 100,
) -> list[StratumRow]:
    """Pull per-pair × per-stratum analyze results with min-N gate annotated.

    Returns `len(pairs) * len(strata)` rows. Each row reports the measured ρ +
    cohort sizes + whether the row passed the min-N gate. Rows that fail the
    gate are kept (NOT dropped) so the caller sees the underpowered cohorts.
    """
    gate = gate or MinNGate()

    # Build the work list
    jobs: list[tuple[str, str, Stratum]] = []
    for a1, a2 in pairs:
        for s in strata:
            jobs.append((a1, a2, s))

    rows: list[StratumRow] = []
    completed = 0
    started_at = time.time()

    def _do(job):
        a1, a2, s = job
        if request_throttle_seconds:
            time.sleep(request_throttle_seconds)
        payload = fetch_analyze(a1, a2, s, cache=cache)
        return _row_from_payload(a1, a2, s, payload, gate)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        # Preserve the (allele_1, allele_2, stratum) tuple per future so an
        # exception still surfaces in a row with the correct labels.
        future_to_job = {ex.submit(_do, j): j for j in jobs}
        for fut in as_completed(future_to_job):
            a1, a2, s = future_to_job[fut]
            try:
                rows.append(fut.result())
            except Exception as exc:  # noqa: BLE001
                rows.append(StratumRow(
                    allele_1=a1, allele_2=a2, stratum=s.label,
                    correlation=None, correlation_type="",
                    n_total=0, n_a1_positive=0, n_a2_positive=0,
                    retained=False, drop_reason=f"exception: {exc}",
                ))
            completed += 1
            if progress_every and completed % progress_every == 0:
                elapsed = time.time() - started_at
                rate = completed / elapsed if elapsed > 0 else 0.0
                print(f"  marco_strata: {completed}/{len(jobs)} "
                      f"({rate:.1f} req/s, retained_so_far="
                      f"{sum(1 for r in rows if r.retained)})")

    return rows


def rows_to_dataframe(rows: Iterable[StratumRow]):
    """Optional pandas helper, kept lazy so deltasci.acquisition stays light."""
    import pandas as pd
    return pd.DataFrame([r.to_dict() for r in rows])
