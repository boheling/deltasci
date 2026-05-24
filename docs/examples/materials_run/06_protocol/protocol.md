# Experiment plan — Multi-task GNN spinel cathode screen + closed-loop synthesis validation

Train a multi-task M3GNet-class GNN on the MP spinel and spinel-adjacent subset for {voltage, decomp_temp, hull_distance}. Apply screen to extended composition space; pick top-20 candidates; synthesize + characterize; report hit-rate against the 4.0V/180°C threshold pair.

## Data acquisition
- **Primary dataset**: Materials Project full catalog (filtered to oxide and oxofluoride spinels and spinel-adjacent space groups)
- **Accession / URL**: https://materialsproject.org via pymatgen.ext.matproj API
- **Access constraints**: free, requires MP API key (registration only)
- **Fallback datasets**: AFLOW, OQMD, ICSD experimental crystal structures (paywalled)

## Steps

### 1. Spinel subset extraction
Query MP for entries with prototype spinel topology; supplement with spinel-adjacent space groups.
- **Inputs**: MP catalog
- **Outputs**: spinel structure list
- **Methods cited**: github.com/materialsproject/pymatgen

### 2. Decomp-temp label harvesting
Mine experimental DSC/TGA decomp temps from thermochemistry tables and DFT-MD literature.
- **Inputs**: spinel structure list
- **Outputs**: decomp temp labels
- **Methods cited**: NIST WebBook

### 3. Featurization
Crystal graph + Voronoi neighbors via pymatgen; Goldschmidt + Hume-Rothery features.
- **Inputs**: structures
- **Outputs**: graph + tabular features
- **Methods cited**: github.com/materialsproject/pymatgen, Xie & Grossman 2018, Phys Rev Lett 120:145301

### 4. Multi-task GNN training
M3GNet-class encoder + 3-head MLP with task-weighted MSE.
- **Inputs**: features, labels
- **Outputs**: trained model
- **Methods cited**: Chen & Ong 2022, Nat Comput Sci 2:718

### 5. Candidate ranking
Apply trained model to extended composition space; rank by joint posterior over thresholds.
- **Inputs**: trained model, candidate compositions
- **Outputs**: top-20 ranked list

### 6. Closed-loop synthesis + characterization
Synthesize top-20 with experimental partner; measure voltage (galvanostatic) + decomp temp (TGA).
- **Inputs**: top-20 list
- **Outputs**: measured properties, hit-rate

## Evaluation
- **Primary metric**: Top-20 synthesis hit-rate (fraction of top-20 candidates with measured V > 4.0V AND decomp > 180°C)
- **Success threshold**: Top-20 hit-rate >= 30% on held-out discovery cohort, compared to <15% expected from random spinel selection
- **Null outcome**: Top-20 hit-rate < 15% falsifies the hypothesis
- **Baselines**: CGCNN single-task voltage screen, MEGNet single-task voltage screen, hull-distance-only filter, random selection from MP spinel set

## Compute
- **Hardware**: 1× A100 (24GB)
- **Estimated runtime**: ~6h training, minutes inference
- **Storage**: ~100GB MP-cache + features
- **Cost estimate**: ~$30 GPU + experimental partner cost

## Timeline
ML stack: 4-6 weeks. Experimental closed-loop: 6-12 months for synthesis + characterization.

## Sample-size justification
MP spinel subset ~500-2000 entries with voltage labels. Decomp-temp labels likely <500. Closed-loop test cohort: 10-20 candidates is the realistic budget for an academic experimental partner.