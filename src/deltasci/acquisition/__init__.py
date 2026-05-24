"""Data-acquisition skills for deltasci.

v0.5.0: discover-api — launch Playwright, capture XHR/fetch traffic during
researcher interaction, identify likely data endpoints, emit a Python
`requests`-based stub.

v0.7.3: marco_strata — per-pair stratified pull against MARCo's `/api/analyze`,
with disk-backed cache and a min-N gate so underpowered cohorts surface as
flagged rows instead of silently dropping.

The discovery solves a real recurring problem in AI4Science: many lab portals
and niche data sources don't have documented APIs but DO expose them via the
network panel of any modern browser. Replicating that "open DevTools, see
what the app calls" workflow as a deltasci subcommand removes weeks of manual
scraper engineering for typical use cases.
"""

from deltasci.acquisition.discover_api import discover_api
from deltasci.acquisition.marco_strata import (
    BY_PARITY_FEMALE,
    BY_SEX,
    BY_TRANSFUSION_LOAD,
    BY_TRANSPLANT_HISTORY,
    FILTER_KEYS,
    MARCO_API_ANALYZE,
    MinNGate,
    OVERALL,
    SENSITIZATION_ROUTES,
    Stratum,
    StratumCache,
    StratumRow,
    fetch_analyze,
    pull_stratified,
    rows_to_dataframe,
)

__all__ = [
    "discover_api",
    # MARCo stratified pull
    "MARCO_API_ANALYZE",
    "FILTER_KEYS",
    "Stratum",
    "OVERALL",
    "BY_SEX",
    "BY_TRANSPLANT_HISTORY",
    "BY_PARITY_FEMALE",
    "BY_TRANSFUSION_LOAD",
    "SENSITIZATION_ROUTES",
    "MinNGate",
    "StratumCache",
    "StratumRow",
    "fetch_analyze",
    "pull_stratified",
    "rows_to_dataframe",
]
