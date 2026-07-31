# Spirtes, Glymour & Scheines (2000) — Causation, Prediction, and Search [NO PDF — stub]

**Citation.** Spirtes P., Glymour C., Scheines R. *Causation, Prediction, and Search.*
2nd edition. MIT Press, 2000 (paperback 2001). Adaptive Computation and Machine
Learning series. ISBN 9780262194402. With additional material by D. Heckerman,
C. Meek, G. F. Cooper, T. Richardson.
DOI: 10.7551/mitpress/1754.001.0001
URL: https://direct.mit.edu/books/monograph/2057/Causation-Prediction-and-Search

**Status.** Book-length; not open access from the official publisher. PDF not downloaded
(would be a copyright-infringing mirror). Stub only.

**Abstract (publisher / verified via search).** The book addresses how to turn
observations into causal knowledge using the formalism of Bayes (causal) networks.
It develops a systematic, graph-theoretic and algorithmic framework for *causal
discovery*: inferring as much as possible about the causal structure (a directed graph,
or an equivalence class of graphs) from statistical data plus background assumptions.
Results are applied across the social, behavioral, and physical sciences.

**Core contributions (the "SGS" framework).**
- **Causal Markov Condition (CMC):** every variable is independent of its non-effects
  (non-descendants) given its direct causes (parents). Connects graph structure to the
  (conditional) independencies in the generated distribution. Equivalent to the
  recursive factorization P(v) = ∏ᵢ P(vᵢ | paᵢ).
- **Faithfulness (Stability):** the *only* (conditional) independencies in the
  distribution are those entailed by the CMC via d-separation — i.e. no independencies
  arise from exact parameter cancellation. CMC + Faithfulness ⇒ d-separation ⟺
  conditional independence.
- **Causal discovery algorithms:** the **PC algorithm** (constraint-based; recovers the
  Markov equivalence class / CPDAG of a DAG under CMC, Faithfulness, acyclicity, causal
  sufficiency) and the **FCI algorithm** (relaxes causal sufficiency, allowing latent
  confounders; outputs a PAG).
- Treatment of **prediction under manipulation** (the "Manipulation Theorem"),
  underdetermination of causal structure, and equivalence classes.

**Relevance to PhysioMap.** This is the canonical reference for the
Causal-Markov-Condition + Faithfulness pair that licenses reading conditional
independencies off a causal graph via **d-separation** — exactly the acyclic criterion
that PhysioMap's **σ-separation reduces to**. The constraint-based discovery machinery
(PC/FCI) is the methodological backdrop for inferring PhysioMap-style edge structure
from data; FCI's latent-confounder handling is relevant wherever PhysioMap admits
unmeasured common causes. Note: SGS is primarily acyclic; PhysioMap's cyclic
(feedback) setting is the generalization addressed by σ-separation (Forré & Mooij) and
cyclic SCMs (Bongers et al.), which extend this foundation.
