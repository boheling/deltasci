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
