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
