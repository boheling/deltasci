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
