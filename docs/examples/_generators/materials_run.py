"""Generate the materials example run.

Same pattern as biomed_run.py: pre-authored 4 rounds + synthesis + protocol +
risks + challenger JSON, all fed through MockLLM scripting. Runs the full
v0.2 pipeline with audit live against PubMed/Crossref/GitHub/etc.
"""

from __future__ import annotations

import json
from pathlib import Path

from deltasci import CoReasoner, Config, load_pack
from deltasci.cli import _write_outputs_staged
from deltasci.llm.mock import MockLLM


IDEA = (
    "Use a graph neural network trained on the Materials Project to identify Li-ion "
    "cathode candidates in the spinel family with predicted voltage > 4.3V and "
    "thermal decomposition onset > 200C."
)


DOMAIN_R1 = """\
The hypothesis sits at the intersection of two well-characterized regimes — the spinel structural family as Li-ion intercalation hosts, and the high-throughput DFT screening tradition exemplified by the Materials Project.

[CLAIM type=published-evidence coverage=well-covered source="Thackeray et al 1983, Mater Res Bull 18:461 — first spinel LiMn2O4 cathode"]The spinel AB2O4 structural family has been a workhorse for Li-ion cathode chemistry since the 1980s, with LiMn2O4 the canonical example.[/CLAIM]

[CLAIM type=published-evidence coverage=well-covered source="Jain et al 2013, APL Materials 1:011002 — Materials Project foundational paper"]The Materials Project provides DFT-computed properties (formation energy, voltage profiles for intercalation reactions, band gaps) for >150,000 inorganic crystal structures with consistent functional choices.[/CLAIM]

[CLAIM type=engineering-precedent coverage=well-covered source="github.com/materialsproject/pymatgen"]Pymatgen is the open-source toolkit for crystal-structure manipulation, MP API access, and structural featurization at scale.[/CLAIM]

[CLAIM type=observation coverage=well-covered source=""]Standard PBE DFT systematically underestimates band gaps and over-stabilizes some metallic ground states; voltage predictions inherit these biases — a 4.3V threshold predicted by PBE may correspond to a different experimental voltage.[/CLAIM]

The unmet need is voltage + thermal-stability co-screening of spinel candidates beyond the Mn/Co/Ni-dominant materials currently in commercial use:

[CLAIM type=published-evidence coverage=sparse source="Whittingham 2014, Chem Rev 114:11414 — cathode review; specific recent thermal-decomposition benchmarks I'd hedge on"]Cobalt-free and reduced-cobalt cathode chemistry is an active push driven by supply-chain concerns; spinel structures are attractive because of the 3D Li-diffusion network and the structural robustness across charge states.[/CLAIM]

[NOVEL_SYNTHESIS rationale="combining hull-energy synthesizability filter + voltage prediction + thermal decomposition prediction in one pipeline is not standard practice — most existing GNN work targets one property at a time"]A multi-task GNN that predicts voltage AND decomposition temperature AND distance-to-hull jointly, then filters by all three thresholds, is the conceptual leap the hypothesis is making.[/NOVEL_SYNTHESIS]

[KNOWLEDGE_GAP category=unpublished-or-pilot-data]Does the lab have synthesis attempts for any of the candidate compositions, with measured voltage and thermal stability? This anchors the falsifiability threshold.[/KNOWLEDGE_GAP]

[KNOWLEDGE_GAP category=niche-subfield]How many spinel-family entries in MP currently carry experimentally-measured voltage labels at sufficient sample size for training (vs purely DFT-computed)? This determines whether the hypothesis is supervised or active-learning-driven.[/KNOWLEDGE_GAP]
"""


ENGINEER_R1 = """\
The data + ML stack is well-trodden for the supervised case; the multi-task framing pushes the design.

**Data representation.**

[CLAIM type=engineering-precedent coverage=well-covered source="github.com/materialsproject/pymatgen"]Pymatgen provides structure parsing + Voronoi-based featurization that maps a crystal to a graph of atoms (nodes) and bonds (edges).[/CLAIM]

[CLAIM type=published-evidence coverage=well-covered source="Xie & Grossman 2018, Phys Rev Lett 120:145301 — CGCNN"]Crystal Graph Convolutional Neural Networks (CGCNN) demonstrated that GNNs over crystal graphs achieve DFT-level accuracy on formation energy, band gap, and other properties at substantially lower compute.[/CLAIM]

[CLAIM type=published-evidence coverage=well-covered source="Chen & Ong 2022, Nat Comput Sci 2:718 — M3GNet"]M3GNet extends graph networks to many-body interactions with a universal interatomic potential, enabling structural relaxation as part of the prediction pipeline.[/CLAIM]

**ML paradigm.**

A multi-task GNN with three regression heads (voltage, decomposition temperature, distance-to-hull) sharing a backbone encoder. The voltage head trains on MP-computed voltages; the thermal head trains on a smaller experimental + DFT decomposition dataset; the hull head trains on MP convex-hull energies.

[CLAIM type=engineering-precedent coverage=well-covered source="github.com/materialsproject/MatBench"]MatBench provides standardized benchmark splits for materials property prediction, including hull energies and band gaps.[/CLAIM]

[CLAIM type=observation coverage=sparse source=""]Combining a multi-task GNN with hull-energy filtering for synthesizability has appeared in recent preprints but I would hedge on specific 2024+ citations.[/CLAIM]

**Existing implementations of the exact idea.**

[KNOWLEDGE_GAP category=niche-subfield]Has multi-task GNN voltage + decomposition co-prediction been published for Li-ion cathodes specifically? I can recall single-task cathode GNN screens but no multi-task pipeline.[/KNOWLEDGE_GAP]

**Compute.**

[CLAIM type=observation coverage=well-covered source=""]Single A100 sufficient. CGCNN/M3GNet-class encoders train in a few GPU-hours on MP-scale (~150K) datasets; inference over the full MP catalog is minutes.[/CLAIM]

**Top three risks.**

1. [CLAIM type=observation coverage=well-covered source=""]Train-test leakage in materials databases via near-duplicate structures across composition or polymorph variants is a documented failure mode for ML-on-MP work.[/CLAIM]

2. [CLAIM type=observation coverage=sparse source=""]Decomposition-temperature labels are sparser and noisier than voltage labels. Class-imbalance in 'thermally-stable above 200°C' may degrade the corresponding head; specific dataset sizes I'd hedge on.[/CLAIM]

3. [CLAIM type=published-evidence coverage=well-covered source="Sun et al 2016, Sci Adv 2:e1600225 — synthesizability vs energy-above-hull"]Distance-to-hull is an imperfect synthesizability proxy — meta-stable phases above the hull do get synthesized, sometimes routinely; a hard hull-distance cutoff will reject viable candidates.[/CLAIM]

[NOVEL_SYNTHESIS rationale="combining classical empirical rules with learned features in a single pipeline is not standard — most GNN cathode work uses pure structural features"]Adding Goldschmidt tolerance factor, ionic-radius mismatch, and Hume-Rothery rules as auxiliary input features alongside the learned graph embedding lets the model exploit hard-won materials-science priors that pure GNN features may not recover from data alone.[/NOVEL_SYNTHESIS]
"""


DOMAIN_R2 = """\
Two adjustments before this is a defensible hypothesis.

**1. The right outcome and the right baseline.**

[CLAIM type=published-evidence coverage=sparse source="Aykol et al 2018, Sci Adv 4:eaaq0148 — synthesizability prediction; specific result numbers I'd hedge on"]Synthesizability prediction has progressed beyond hull-distance to multi-feature classification; any new screen should compare against this stronger baseline.[/CLAIM]

[CLAIM type=observation coverage=well-covered source=""]A hard 4.3V threshold misses physically interesting compounds at 4.25V or 4.35V — voltage prediction has known DFT-systematic error of roughly ±0.1-0.2V depending on the redox couple. Pre-screening should use a soft margin, with the hard threshold reserved for the final candidate list.[/CLAIM]

**2. Clinically meaningful evaluation — i.e., synthesis-meaningful.**

[CLAIM type=engineering-precedent coverage=well-covered source="github.com/materialsproject/MatBench"]The MatBench benchmark protocol for materials property prediction includes scaled MAE and R² but not synthesizability hit-rate, which is the metric that matters for an actionable cathode screen.[/CLAIM]

[NOVEL_SYNTHESIS rationale="connecting GNN screen output to experimental synthesizability validation has been done individually but not as a held-out evaluation regime"]The right held-out test is not 'predict the test-set MP voltage' — it is 'pick top-K candidates from outside MP, attempt synthesis, measure properties, compute hit-rate against the predicted thresholds.' This is a closed-loop evaluation, more demanding than benchmark MAE.[/NOVEL_SYNTHESIS]

**3. The falsifiable prediction.**

The hypothesis should commit to: a multi-task GNN, trained on MP plus the available experimental decomposition data, achieves a top-20 synthesis hit-rate ≥ 30% on a held-out test cohort of synthesized + characterized spinel candidates outside the MP-training set, with measured voltage > 4.0V (allowing 0.3V DFT-error tolerance from the 4.3V design target) AND measured decomposition onset > 180°C (20°C tolerance from 200°C target). Hit-rate < 15% falsifies it.

[KNOWLEDGE_GAP category=lab-tribal-knowledge]Is there an experimental partner who can synthesize and characterize the top-K candidates from the screen? Without this, the falsifiability prediction is computational only and the hypothesis collapses to a benchmark exercise.[/KNOWLEDGE_GAP]
"""


ENGINEER_R2 = """\
Adopting the domain refinements. The pivot: shift evaluation from 'MP test-set MAE' to 'top-K synthesis hit-rate.' This changes the model design and the training data substantially.

**Architecture.**

Per-crystal graph G = (V, E):
- V = atoms with Voronoi-defined neighbor sets, plus learned embeddings for element + oxidation state
- E = bonds with edge-features for distance + bond type

Encoder: 3-layer M3GNet-class graph backbone (hidden_dim=128) → graph readout (mean + sum pool concatenated) → concatenated with hand-engineered features (Goldschmidt tolerance factor, average ionic radius mismatch, mean electronegativity difference) → 3-head MLP for {voltage, decomp_temp, hull_distance}.

[CLAIM type=published-evidence coverage=well-covered source="Chen & Ong 2022, Nat Comput Sci 2:718 — M3GNet"]The published M3GNet architecture provides the universal-potential encoder; pymatgen provides the hand-engineered features as 1-line calls.[/CLAIM]

[KNOWLEDGE_GAP category=niche-subfield]The current canonical maintained M3GNet implementation (the materialsvirtuallab fork or the newer matgl combined library — please supply the correct verified GitHub URL).[/KNOWLEDGE_GAP]

**Loss.**

Multi-task with task-dependent weights:
- L_voltage = MSE on MP-computed voltages (large, noisy, dense)
- L_decomp = MSE on experimental + DFT-MD decomp temps (small, sparser)
- L_hull = MSE on MP hull distances (large, dense)
- λ_v = 1.0, λ_d = 0.5 (smaller dataset weighted up via uncertainty), λ_h = 0.3

**Training plan.**

1. Source: MP catalog (full inorganic), filtered to oxide and oxofluoride spinels and spinel-adjacent topologies.
2. Decomposition labels: harvest experimental DSC/TGA data from open thermochemistry tables + literature mining (~few thousand labels at most, sparse).
3. Stratified split by composition (no leakage of composition between train/test).
4. Held-out 'discovery test' cohort: 10-20 candidates outside MP (from recent ICSD additions or novel compositions), synthesized in collaboration; measured voltage and decomp temp.
5. Baselines: CGCNN single-task voltage, MEGNet single-task voltage, hull-distance-only filter, random selection from spinel structure.

**Expected outcomes.**

[CLAIM type=observation coverage=sparse source=""]Realistic top-20 synthesis hit-rate for a well-tuned multi-task screen is plausibly 25-40% on a focused spinel test cohort; below 15% means the screen is no better than randomly picking from the MP spinel set.[/CLAIM]

[KNOWLEDGE_GAP category=unpublished-or-pilot-data]Pilot synthesis attempts on the top-3 candidates from a baseline single-task screen would calibrate the hit-rate threshold and inform the +0.3V tolerance band on the 4.3V target.[/KNOWLEDGE_GAP]

**Compute & timeline.**

[CLAIM type=observation coverage=well-covered source=""]Single A100; ~6 hours total training. The dominant timeline cost is the experimental closed-loop validation — 6-12 months for a 10-20 candidate synthesis + characterization round.[/CLAIM]
"""


SYNTHESIS_JSON = json.dumps({
    "title": "Multi-task GNN for spinel Li-ion cathode discovery: voltage + thermal stability co-prediction",
    "statement": (
        "A multi-task graph neural network trained on Materials Project structural and computed-voltage data, "
        "with auxiliary heads for thermal decomposition temperature and energy-above-hull, will identify spinel "
        "Li-ion cathode candidates that achieve a top-20 synthesis hit-rate ≥ 30% on a closed-loop experimental "
        "validation cohort, where 'hit' means measured voltage > 4.0V AND decomposition onset > 180°C."
    ),
    "domain_grounding": {
        "mechanism": "Spinel AB2O4 structural family is a documented Li-ion cathode workhorse; multi-task GNNs over crystal graphs achieve DFT-level accuracy at substantially lower compute; multi-task auxiliary supervision regularizes the dominant voltage-prediction task and provides synthesizability filtering at inference time.",
        "unmet_need": "Cobalt-reduced cathode discovery requires voltage + thermal stability + synthesizability co-screening at scale; existing screens optimize one property at a time, and synthesizability proxies are weak.",
        "expected_impact": "An auditable closed-loop screen that retires non-viable candidates before synthesis, focusing experimental effort on the highest-probability hits."
    },
    "technical_approach": {
        "core_method": "M3GNet-class crystal-graph encoder + 3-head MLP for voltage / decomposition temperature / hull distance, with hand-engineered Goldschmidt + Hume-Rothery features concatenated to the graph readout.",
        "key_innovation": "Multi-task auxiliary supervision combined with classical empirical-rule features on a unified GNN backbone, validated on closed-loop experimental synthesis hit-rate rather than benchmark MAE.",
        "implementation_path": "MP catalog filtered to spinels + spinel-adjacent → harvest decomp-temp labels → stratified-by-composition split → multi-task M3GNet training → top-K candidate selection → external synthesis + characterization → hit-rate evaluation."
    },
    "falsifiability": {
        "prediction": "The multi-task GNN screen achieves a higher top-20 synthesis hit-rate on a held-out spinel discovery cohort than single-task voltage-only baselines and a hull-distance-only filter.",
        "threshold": "Top-20 hit-rate >= 30% (where 'hit' = measured voltage > 4.0V AND decomp onset > 180°C), compared to baseline hit-rate that must be empirically established but is expected near 10-15% from random spinel selection.",
        "null_outcome": "Top-20 hit-rate < 15% falsifies the hypothesis: the multi-task screen is no better than random spinel selection from the MP catalog."
    },
    "feasibility_scores": {
        "data_availability": 4,
        "technical_feasibility": 4,
        "physical_plausibility": 4,
        "novelty": 3,
        "synthesizability": 2
    },
    "feasibility_justifications": {
        "data_availability": "MP voltage data is dense; thermal decomp labels require literature mining and are the bottleneck.",
        "technical_feasibility": "M3GNet + multi-task heads are well-trodden engineering; ~1 week of training/eval.",
        "physical_plausibility": "Spinel as cathode, hull-distance as synthesizability proxy, and Hume-Rothery / Goldschmidt features all have decades of physical grounding.",
        "novelty": "Multi-task GNN for one-shot cathode property co-prediction is incremental over single-task work but not transformative.",
        "synthesizability": "Closed-loop experimental validation is the key bottleneck — requires an experimental partner with 6-12 month synthesis turnaround on novel spinel compositions."
    }
}, indent=2)


PROTOCOL_JSON = json.dumps({
    "title": "Multi-task GNN spinel cathode screen + closed-loop synthesis validation",
    "summary": "Train a multi-task M3GNet-class GNN on the MP spinel and spinel-adjacent subset for {voltage, decomp_temp, hull_distance}. Apply screen to extended composition space; pick top-20 candidates; synthesize + characterize; report hit-rate against the 4.0V/180°C threshold pair.",
    "data_acquisition": {
        "primary_dataset": "Materials Project full catalog (filtered to oxide and oxofluoride spinels and spinel-adjacent space groups)",
        "accession_or_url": "https://materialsproject.org via pymatgen.ext.matproj API",
        "access_constraints": "free, requires MP API key (registration only)",
        "fallback_datasets": ["AFLOW", "OQMD", "ICSD experimental crystal structures (paywalled)"]
    },
    "steps": [
        {"order": 1, "name": "Spinel subset extraction", "description": "Query MP for entries with prototype spinel topology; supplement with spinel-adjacent space groups.",
         "inputs": ["MP catalog"], "outputs": ["spinel structure list"],
         "method_citations": ["github.com/materialsproject/pymatgen"]},
        {"order": 2, "name": "Decomp-temp label harvesting", "description": "Mine experimental DSC/TGA decomp temps from thermochemistry tables and DFT-MD literature.",
         "inputs": ["spinel structure list"], "outputs": ["decomp temp labels"],
         "method_citations": ["NIST WebBook"]},
        {"order": 3, "name": "Featurization", "description": "Crystal graph + Voronoi neighbors via pymatgen; Goldschmidt + Hume-Rothery features.",
         "inputs": ["structures"], "outputs": ["graph + tabular features"],
         "method_citations": ["github.com/materialsproject/pymatgen", "Xie & Grossman 2018, Phys Rev Lett 120:145301"]},
        {"order": 4, "name": "Multi-task GNN training", "description": "M3GNet-class encoder + 3-head MLP with task-weighted MSE.",
         "inputs": ["features", "labels"], "outputs": ["trained model"],
         "method_citations": ["Chen & Ong 2022, Nat Comput Sci 2:718"]},
        {"order": 5, "name": "Candidate ranking", "description": "Apply trained model to extended composition space; rank by joint posterior over thresholds.",
         "inputs": ["trained model", "candidate compositions"], "outputs": ["top-20 ranked list"],
         "method_citations": []},
        {"order": 6, "name": "Closed-loop synthesis + characterization", "description": "Synthesize top-20 with experimental partner; measure voltage (galvanostatic) + decomp temp (TGA).",
         "inputs": ["top-20 list"], "outputs": ["measured properties", "hit-rate"],
         "method_citations": []}
    ],
    "primary_metric": "Top-20 synthesis hit-rate (fraction of top-20 candidates with measured V > 4.0V AND decomp > 180°C)",
    "success_threshold": "Top-20 hit-rate >= 30% on held-out discovery cohort, compared to <15% expected from random spinel selection",
    "null_outcome": "Top-20 hit-rate < 15% falsifies the hypothesis",
    "baselines": ["CGCNN single-task voltage screen", "MEGNet single-task voltage screen", "hull-distance-only filter", "random selection from MP spinel set"],
    "compute": {"hardware": "1× A100 (24GB)", "estimated_runtime": "~6h training, minutes inference", "storage": "~100GB MP-cache + features", "cost_estimate": "~$30 GPU + experimental partner cost"},
    "timeline_estimate": "ML stack: 4-6 weeks. Experimental closed-loop: 6-12 months for synthesis + characterization.",
    "sample_size_justification": "MP spinel subset ~500-2000 entries with voltage labels. Decomp-temp labels likely <500. Closed-loop test cohort: 10-20 candidates is the realistic budget for an academic experimental partner."
}, indent=2)


RISKS_JSON = json.dumps({
    "summary": "Five risks. The dominant ones are decomp-temp data sparsity, weak synthesizability proxy, and the closed-loop experimental partnership being on the critical path.",
    "items": [
        {"id": "R1", "category": "data", "severity": "high",
         "description": "Decomposition-temperature labels are sparse (likely <500 across all spinels) and noisy (different DSC/TGA protocols, atmospheres). The decomp head will struggle.",
         "likely_failure_mode": "decomp-temp predictions have high variance; the joint hit-rate metric is dominated by decomp filter mistakes.",
         "mitigation": "Begin with a binary 'thermally stable above 200°C: yes/no' classification head if regression is too sparse; consider DFT-MD as label augmentation.",
         "counter_evidence_citations": []},
        {"id": "R2", "category": "method", "severity": "high",
         "description": "Distance-to-hull is a documented imperfect synthesizability proxy. Real synthesizability depends on kinetics, precursor availability, and reaction pathways the GNN cannot see.",
         "likely_failure_mode": "model rejects synthesizable meta-stable spinels; alternatively keeps thermodynamically stable but kinetically inaccessible structures.",
         "mitigation": "Use Aykol et al 2018 multi-feature synthesizability classifier as a secondary filter; relax hull-distance cutoff and rely on closed-loop feedback.",
         "counter_evidence_citations": ["Sun et al 2016, Sci Adv 2:e1600225", "Aykol et al 2018, Sci Adv 4:eaaq0148"]},
        {"id": "R3", "category": "evaluation", "severity": "high",
         "description": "Top-20 hit-rate is a small-N metric (n=20). Statistical significance of a 30% vs 15% hit-rate at n=20 has wide CIs (binomial CI ~[12, 54%] vs [3, 38%]) — overlapping intervals are likely.",
         "likely_failure_mode": "model achieves hit-rate that visually exceeds baseline but does not reach statistical significance.",
         "mitigation": "Pre-register a second screen at n=40 if first screen is ambiguous; report Bayesian posterior on hit-rate, not binary success.",
         "counter_evidence_citations": []},
        {"id": "R4", "category": "external-validity", "severity": "medium",
         "description": "Held-out cohort selected from compositions adjacent to MP training set may share local structural patterns; performance on truly novel compositions may degrade.",
         "likely_failure_mode": "model performs well on near-training-distribution candidates but poorly on out-of-distribution proposals.",
         "mitigation": "Compose held-out set from intentionally distant compositions; report performance stratified by Tanimoto-distance to nearest training neighbor.",
         "counter_evidence_citations": []},
        {"id": "R5", "category": "incentive-or-process", "severity": "medium",
         "description": "Closed-loop synthesis partnership is on the critical path. If the experimental partner deprioritizes the project, the falsifiability evaluation cannot complete.",
         "likely_failure_mode": "ML model trained but never validated experimentally; the project produces a benchmark paper, not a hypothesis test.",
         "mitigation": "Lock in experimental partner with explicit milestone agreement before commencing modeling.",
         "counter_evidence_citations": []}
    ]
}, indent=2)


CHALLENGE_JSON = json.dumps({
    "summary": "Four findings. The hypothesis frames the multi-task GNN approach as the novel contribution, but the harder unsolved problem is the decomp-temp data scarcity. The 30% hit-rate threshold is loose given measurement noise. The hull-distance synthesizability filter is doing more inferential work than the framing acknowledges.",
    "findings": [
        {"id": "C1", "kind": "feasibility-overstated", "severity": "high",
         "description": "The 30% top-20 hit-rate threshold at n=20 has a wide binomial CI (~[12%, 54%]). A baseline screen at hit-rate 15% has CI ~[3%, 38%]. The two CIs overlap substantially, so a measured 30% vs 15% point estimate is not a definitive falsifiability test at this sample size.",
         "evidence_citations": [],
         "suggested_response": "Pre-specify n=40 or report Bayesian posterior on hit-rate; treat the threshold as a Bayesian prior, not a frequentist gate."},
        {"id": "C2", "kind": "novelty-overstated", "severity": "medium",
         "description": "Multi-task GNNs for materials property co-prediction have appeared in the recent literature. The OS-specific contribution is the spinel + decomp-temp + closed-loop angle, not the multi-task GNN itself.",
         "evidence_citations": ["Chen & Ong 2022, Nat Comput Sci 2:718"],
         "suggested_response": "Frame the contribution as the spinel + closed-loop synthesis evaluation, not the architecture."},
        {"id": "C3", "kind": "missing-baseline", "severity": "high",
         "description": "Hull-distance-only filter is too easy a baseline. Stronger baselines: (a) Aykol synthesizability classifier with hull as one feature, (b) bandit-style active learning that picks batch candidates rather than top-K static, (c) random forest on the same hand-engineered features without GNN.",
         "evidence_citations": ["Aykol et al 2018, Sci Adv 4:eaaq0148"],
         "suggested_response": "Add (a)-(c) as required baselines; if multi-task GNN does not beat random forest on the same features, the GNN was unnecessary."},
        {"id": "C4", "kind": "data-leakage-risk", "severity": "medium",
         "description": "Stratified-by-composition split helps but does not eliminate near-duplicate-structure leakage when the same composition has multiple polymorphs in MP. Polymorph-aware split is needed.",
         "evidence_citations": [],
         "suggested_response": "Split by reduced-formula AND prototype-structure tag jointly; report the training-set leak rate explicitly."}
    ]
}, indent=2)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    out_dir = repo_root / "examples" / "materials_run"
    out_dir.mkdir(parents=True, exist_ok=True)

    pack = load_pack("materials")
    llm = MockLLM(responses=[
        DOMAIN_R1, ENGINEER_R1, DOMAIN_R2, ENGINEER_R2,
        SYNTHESIS_JSON, PROTOCOL_JSON, RISKS_JSON, CHALLENGE_JSON,
    ])
    config = Config(
        num_rounds=4,
        grounding_strictness="high",
        require_falsifiability=True,
        require_epistemic_humility=True,
        generate_protocol=True,
        generate_risks=True,
        run_challenge=True,
        auto_view=False,
        output_dir=out_dir,
    )
    reasoner = CoReasoner(pack=pack, llm=llm, config=config)
    result = reasoner.run(idea=IDEA)
    _write_outputs_staged(result, out_dir, IDEA, pack=pack, generate_notebook=True)

    es = result.hypothesis.epistemic_summary
    audit = result.audit_report
    print(f"materials_run (v0.2.0) generated:")
    print(f"  well-covered: {es.well_covered_count} · sparse: {es.sparse_count} · gaps: {es.knowledge_gap_count} · syntheses: {es.novel_synthesis_count}")
    print(f"  protocol steps: {len(result.plan.steps)} · risks: {len(result.risks.items)} · challenge findings: {len(result.challenge.findings)}")
    print(f"  audit: {audit.banner()}")
    if audit.mismatch_count:
        print()
        for f in audit.findings:
            if f.status != "mismatch":
                continue
            print(f"  ✗ [{f.auditor_name}] AI claimed: {f.target_summary[:100]}")
            for r in f.mismatch_reasons:
                print(f"      → {r}")
    print(f"  outputs in {out_dir}")


if __name__ == "__main__":
    main()
