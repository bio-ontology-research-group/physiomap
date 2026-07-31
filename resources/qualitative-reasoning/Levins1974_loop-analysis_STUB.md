# Levins 1974 — The Qualitative Analysis of Partially Specified Systems  [NO PDF — stub]

**Full citation.** Levins, R. (1974). "Discussion Paper: The Qualitative Analysis of
Partially Specified Systems." *Annals of the New York Academy of Sciences*, 231(1),
123–138.
**DOI:** 10.1111/j.1749-6632.1974.tb20562.x
**URL:** https://nyaspubs.onlinelibrary.wiley.com/doi/10.1111/j.1749-6632.1974.tb20562.x

**Companion (also stubbed here):** Puccia, C. J. & Levins, R. (1985). *Qualitative
Modeling of Complex Systems: An Introduction to Loop Analysis and Time Averaging.*
Harvard University Press. (The canonical book-length treatment of loop analysis.)

**Status.** Paywalled (Wiley; WebFetch returned HTTP 402). PDF not obtained. Summary
below is reconstructed from verified bibliographic metadata and multiple secondary
descriptions of loop analysis (Justus/Dinno loop-analysis tutorials, the `LoopAnalyst`
R package documentation, and Puccia & Levins). Treat as a stub, not a read of the
primary text.

## Summary (from secondary sources)
Levins introduced **loop analysis** for systems we know only qualitatively: we know the
*sign* of each direct interaction between variables (the sign pattern of the Jacobian /
**community matrix** at equilibrium), but not the magnitudes. The system is drawn as a
**signed digraph**: a directed edge i←j with sign = sign(∂(dx_i/dt)/∂x_j). A *loop* of
length k is a set of k variables connected in a closed chain; its sign is the product of
the edge signs around it; its value is the product of the interaction magnitudes.

Key constructs:
- **Self-loops** a_ii (diagonal) = self-regulation; negative self-loops = damping.
- **Feedback at level k**, F_k = (signed, weighted) sum of all disjoint loop products
  spanning k variables; F_k is (up to sign) the k-th coefficient of the characteristic
  polynomial of the community matrix.
- **Stability (Routh–Hurwitz, qualitative form):** requires F_k < 0 for all k (every
  feedback level negative) *and* Hurwitz determinant conditions; intuitively, no positive
  feedback loop may dominate. Higher-level (long) positive loops are the usual source of
  instability.
- **Press perturbation / comparative statics:** the response of equilibrium x*_i to a
  sustained parameter change c_h is obtained from **complementary feedback** terms,
  effectively a signed-cofactor / adjugate expression:
  ∂x*_i/∂c_h = − [ Σ (path from h to i) · (complementary feedback of the rest) ] / F_n.
  When the numerator mixes opposite signs, the prediction is **ambiguous ('?')** — exactly
  the indeterminate-sign situation PhysioMap logs.

## Relevance to PhysioMap
This is the **biological/ecological lineage** of PhysioMap's solver and the closest
classical analogue to what `qualitative.py` does. Loop analysis already:
1. works on a **cyclic signed graph** (unlike Wellman's acyclic QPN), which is the
   PhysioMap setting;
2. derives **sign(∂x*/∂θ)** at a steady state from sign pattern alone — i.e. qualitative
   comparative statics — via signed sums of paths × complementary feedback (this is the
   adjugate/Cramer structure underlying sign-solvability);
3. makes **stability** (negative feedback at every level; dominant self-regulation) the
   precondition that lets signs be determined — matching PhysioMap's "negative diagonal /
   dominant self-regulation" assumption;
4. returns **ambiguity** when path contributions of opposite sign collide — PhysioMap's
   '?'. The "table of predictions" in Puccia & Levins is literally a sign-prediction matrix
   with entries +, −, 0, and ambiguous.

**Implementation cue:** the press-perturbation formula = signed cofactor expansion of
(−J). PhysioMap's SCC sign-solving is the matrix-algebra version of Levins' loop/feedback
bookkeeping; the loop view is the better tool for *explaining why* a sign is ambiguous
(which loops conflict).
