# Case study — `deltasci discover-api` against MARCo

**Date**: 2026-05-02
**Tool**: `deltasci discover-api` (v0.5.0)
**Target**: `https://marco.igen.org.br/`
**Goal**: confirm that the Playwright-based capture identifies real data endpoints on a JS-rendered AI4Science portal and produces a usable Python stub.

## Result: 3 endpoints discovered + 1 unblocks the entire MARCo pipeline

### Identified endpoints (heuristic-ranked)

| Rank | Method | Path | Score | Why it scored | Use |
|------|--------|------|-------|---------------|-----|
| 1 | `POST` | `/api/correlation-matrix` | 11.00 | same-origin · `/api/` · `/correlation` · 380KB JSON · POST payload · 200 OK | **bulk pull** — all pairs for a locus group in one call |
| 2 | `POST` | `/api/analyze` | 9.50 | same-origin · `/api/` · 200KB JSON · array · POST payload · 200 OK | per-pair detailed view (single allele1+allele2 query) |
| 3 | `GET`  | `/api/options` | 8.00 | same-origin · `/api/` · 6KB JSON · array · 200 OK | dictionary: valid alleles, manufacturers, locus groups, kits, sex/transfusion/transplant filter values |

### What this changes about the marco_dr_dq hypothesis

Before discover-api (the v0.4 case study assumption):

> "MARCo bulk extraction may take 2 months instead of 1-2 weeks; partial coverage forces the analysis to subset, undermining per-locus claims." — risk R1, severity **critical**.

After discover-api:

> Three POST requests (~30 seconds total) pull **10,796 Class II pairs**, including **2,608 with paired Immucor + OneLambda coverage** — the exact subset the platform-discrepancy analysis needs. Risk R1 collapses from "critical, blocking" to "trivial."

### Real numbers (pulled live from the API)

| Locus group | Total pairs | Loci covered | Paired Immucor+OL pairs |
|-------------|-------------|---------------|-------------------------|
| `DRDQDP` | 10,796 | DPB1, DQB1, DRB1, DRB3, DRB4, DRB5 | 2,608 |
| `DRB345` | 1,333 | DRB1, DRB3, DRB4, DRB5 | 595 |
| `DQB1` | 846 | DQB1 | 190 |
| `DPB1` | 1,324 | DPB1 | 145 |

### Real-world findings the AI couldn't have guessed

The discover-api flow surfaced facts that no amount of generated scaffolding could have known:

- **Locus naming**: MARCo's `matrix_options` has `A`, `B`, `C`, `ABC`, `DPB1`, `DQB1`, `DRB345`, `DRDQDP` — there is **no standalone `DRB1`, `DQA1`, `DPA1`** at the matrix level. The DRB345 group is combined; DQA1 and DPA1 are folded into DRDQDP.
- **Per-platform rho**: the bulk endpoint returns ONE manufacturer's view per call. To get `rho_pooled` + `rho_immucor` + `rho_ol` per pair, you make THREE calls (`manufacturer_kit ∈ {All_Manufacturers_Kits, Immucor, OneLambda}`) and join on `(allele_1, allele_2)`.
- **Mismatch encoding**: `allele_1_mismatches` is a string like `"1 (0.34%)"`, not a numeric column — needs parsing.
- **The `hover_text` column** is a pre-rendered HTML tooltip suitable for cross-checking that your numeric parse matches what the UI displays.

### The full bulk-pull recipe (now usable in marco_dr_dq notebook)

```python
import requests

def fetch_marco_matrix(locus_group: str, manufacturer_kit: str = "All_Manufacturers_Kits") -> dict:
    r = requests.post(
        "https://marco.igen.org.br/api/correlation-matrix",
        json={"manufacturer_kit": manufacturer_kit, "locus_group": locus_group},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()

# Pull DRDQDP three times for platform-stratified rho
pooled  = fetch_marco_matrix("DRDQDP", "All_Manufacturers_Kits")["matrix_data"]
immucor = fetch_marco_matrix("DRDQDP", "Immucor")["matrix_data"]
onelamb = fetch_marco_matrix("DRDQDP", "OneLambda")["matrix_data"]
# Join on (allele_1, allele_2) → DataFrame with rho_pooled, rho_immucor, rho_ol
```

## Lessons from running discover-api end-to-end

### What worked

1. **Heuristic scoring is sufficient** for this site. The top-ranked endpoint (correlation-matrix) is exactly what the marco_dr_dq notebook needs. No LLM call required.
2. **Capture during natural interaction** — locale-switch and slider-drag triggered fresh requests; that was enough to surface all 3 endpoints.
3. **The generated `api_stub.py`** preserves the captured POST payload as the default, so the call-shape is correct on first try.
4. **Same-origin + `/api/` path heuristic** correctly filtered out static assets, tracking pixels, and CDN traffic.

### What needed manual follow-up

1. **Locus naming validation**: the auto-generated stub had `"locus_group": "A"` (the captured default). For DR/DQ work, that's the wrong value. The user has to inspect `endpoints.json` for the `matrix_options` enum.
2. **Per-platform iteration**: the stub calls `correlation-matrix` once. The actual research workflow needs 3 calls (one per `manufacturer_kit`). That's a researcher synthesis step, not auto-derivable.
3. **Validation errors on invalid locus_group**: 422 errors are clear but not annotated in the stub.

### Implications for v0.5.1

- **LLM-driven endpoint analysis would help here**: given `--describe "per-allele-pair MFI Spearman correlation across both Immucor and OneLambda platforms"`, an LLM could read endpoints.json and produce a stub that loops over manufacturers + handles the join.
- **Param-space inference**: when an endpoint accepts an enum (locus_group, manufacturer_kit), the stub should enumerate the valid values from `/api/options` automatically.
- **Multi-endpoint workflows**: the stub generator currently emits ONE function for the top-ranked endpoint. A "workflow" output that chains options → bulk-matrix would be more useful for sites like MARCo.

These are the right v0.5.1 priorities — not because the v0.5.0 heuristic mode failed, but because it surfaced exactly the limits where LLM augmentation would add real value.

## Files in this case study directory

- **`endpoints.json`** — full captured + ranked endpoint list (3 entries with response shapes)
- **`api_stub.py`** — auto-generated Python stub for the top-ranked endpoint
- **`SUMMARY.md`** — this document
