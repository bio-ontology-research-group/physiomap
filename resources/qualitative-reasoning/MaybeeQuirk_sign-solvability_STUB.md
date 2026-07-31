# Sign-solvability & qualitative economics  [NO PDF — stub]

Covers the matrix-theory lineage of PhysioMap's comparative-statics step. Several closely
related classics are grouped here because they form one body of theory.

## Primary references
1. **Maybee, J. & Quirk, J. (1969).** "Qualitative Problems in Matrix Theory."
   *SIAM Review*, 11(1), 30–51. DOI: 10.1137/1011004.
   URL: https://epubs.siam.org/doi/10.1137/1011004
2. **Bassett, L., Maybee, J. & Quirk, J. (1968).** "Qualitative Economics and the Scope of
   the Correspondence Principle." *Econometrica*, 36(3–4), 544–563. (Origin of the
   sign-nonsingular / sign-solvability program.)
3. **Lancaster, K. (1962).** "The Scope of Qualitative Economics." *Review of Economic
   Studies* 29(2):99–123; **Lancaster, K. (1965).** "The Theory of Qualitative Linear
   Systems." *Econometrica* 33(2):395–408.
4. **Samuelson, P. A. (1947).** *Foundations of Economic Analysis.* Harvard UP. — origin
   of the **correspondence principle**: stability (dynamic) conditions supply sign
   information used in comparative statics.
5. **Brualdi, R. A. & Shader, B. L. (1995).** *Matrices of Sign-Solvable Linear Systems.*
   Cambridge Tracts in Mathematics 116. — the modern, coherent synthesis.

**Status.** All paywalled (SIAM/Econometrica/CUP; WebFetch blocked 403/402). No PDF
obtained. The definitions below are reconstructed from **verified search-result summaries**
of these works (incl. Brualdi's own preface page and the Brualdi–Shader book description)
and are standard textbook statements; treat as a grounded stub, not a primary read.

## The core definitions (verified from secondary sources)
- A linear system **Ax = b** is **sign-solvable** iff it is solvable *and* the sign pattern
  of the solution x is uniquely determined by the sign patterns of A and b alone (every
  real matrix/vector with the same sign pattern gives an x with the same sign pattern).
- **A is sign-nonsingular (SNS)** iff every real matrix with the same sign pattern as A is
  nonsingular. Equivalently: in the standard determinant expansion
  det A = Σ_σ sgn(σ) Π_i a_{i σ(i)}, **every nonzero term has the same sign** (no
  cancellation possible). This is the combinatorial heart of sign-solvability.
- **L-matrix:** an m×n (0,±1) sign pattern whose every real realization has linearly
  independent rows. Square L-matrices = SNS matrices.
- **Signed-digraph criterion:** sign-nonsingularity / sign-determinacy can be read off the
  signed digraph of A — e.g. via conditions on the signs of cycles (an even/odd cycle
  characterization for SNS matrices). This connects directly to Levins' loop analysis.

## Why this is the math under PhysioMap
PhysioMap's comparative statics at steady state is: J·(dx*) = −(∂f/∂θ)·dθ, so
**dx* = −J⁻¹ · b**, with b = (∂f/∂θ)dθ. The Quirk–Maybee/Lancaster question is *exactly*
PhysioMap's question:

> When is sign(dx*) = sign(−J⁻¹ b) determined by the **sign patterns of J and b alone**,
> with no magnitudes?

Answer (the rule to implement):
- Compute each component via Cramer: dx*_i = det(J with column i replaced by −b) / det J.
- The sign is **determinate** iff (a) det J is sign-determinate (J near-SNS up to a global
  sign — guaranteed structurally if J has a negative-dominant diagonal / is sign-stable),
  **and** (b) the numerator determinant is sign-determinate, i.e. **all surviving terms in
  its signed expansion share one sign** (no opposing paths). 
- Otherwise return **'?'**. The '?' is not failure; it is the honest statement that two
  real systems with this sign pattern give opposite-sign responses.

**Stability ⇒ determinacy (correspondence principle).** Samuelson's insight, formalized by
Bassett–Maybee–Quirk: assuming the equilibrium is **stable** pins down the sign of det J
(for a stable n×n system sign(det J) = (−1)ⁿ) and supplies the diagonal-dominance that
makes many numerators sign-determinate. This is precisely PhysioMap's "stability assumed
(negative diagonal / dominant self-regulation)" decision — it is what *licenses* sign-only
comparative statics.

## Relevance to PhysioMap (highest value)
- **This is the named method PhysioMap chose** ("Quirk–Maybee/Lancaster sign-solvability,
  no Monte Carlo"). The SNS / single-sign-of-all-determinant-terms test is the exact
  decision procedure for `qualitative.py`'s SCC solver.
- Implement determinacy as: sign-expansion of the relevant determinants; if any two terms
  disagree in sign → '?'. Use diagonal sign + stability to fix sign(det J).
- Brualdi–Shader gives polynomial algorithms (matching / signed-digraph) to test
  sign-nonsingularity — worth consulting if the naive determinant expansion is too slow on
  large SCCs.
