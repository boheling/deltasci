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
