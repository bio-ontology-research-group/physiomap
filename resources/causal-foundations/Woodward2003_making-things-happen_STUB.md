# Woodward (2003) — Making Things Happen: A Theory of Causal Explanation [NO PDF — stub]

**Citation.** Woodward J. *Making Things Happen: A Theory of Causal Explanation.*
Oxford University Press, 2003. Oxford Studies in Philosophy of Science.
ISBN 9780195155273. DOI: 10.1093/0195155270.001.0001
URL: https://doi.org/10.1093/0195155270.001.0001

**Status.** Book-length, paywalled (OUP). PDF not downloaded. Stub only.
The interventionist definitions below were verified against Woodward's own restatements
(e.g. "Causation with a Human Face", read locally; and the standard published statement
of I1–I4) — they are the canonical, widely-quoted formulations.

**Abstract.** Woodward gives a unified *interventionist* (manipulationist) account of
causation and causal explanation. The central thesis: causal claims are claims about
what *would happen to Y under hypothetical interventions on X*. Rather than reducing
causation to non-causal terms, the theory explicates a rich variety of causal notions
(direct, contributing, total cause; actual causation; explanation) in terms of one
primitive causal concept — the **intervention** — and the invariance of relationships
under such interventions.

## The interventionist account (precise statements)

**Intervention variable.** I is an *intervention variable* for X with respect to Y iff:
- **(I1)** I causes X.
- **(I2)** I acts as a *switch* for all other causes of X: for some values of I, X ceases
  to depend on its other causes and depends only on I (I "breaks the arrows" into X).
- **(I3)** Any directed path from I to Y goes *through* X. (I does not affect Y directly,
  nor via causes of Y distinct from X, except those on the I→X→Y route.)
- **(I4)** I is (statistically) independent of any variable Z that causes Y and lies on a
  directed path that does not go through X.

**Intervention.** A change in the value of X is an *intervention* (on X with respect to
Y) if it is brought about by an intervention variable I in the above sense — i.e. an
exogenous, surgical setting of X that disrupts X's other causes but leaves the rest of
the system's mechanisms intact.

**(M) Direct cause.** X is a **direct cause** of Y (with respect to a variable set V) iff
there is a *possible intervention* on X that changes Y (or the probability distribution
of Y) *while all other variables in V are held fixed at some value by interventions*.

**Contributing (total) cause.** X is a **contributing cause** of Y iff there is a
directed path of direct-causal links from X to Y such that there is a *possible
intervention* on X that changes Y, when other variables not on that path are held fixed —
i.e. X makes a difference to Y along at least one route under intervention.

## Relevance to PhysioMap

This is the **philosophical justification for PhysioMap's edge semantics.** PhysioMap
edges are explicitly *interventionist*: an edge X→Y asserts that a (possible) surgical
intervention on X would change Y with the rest of the system held fixed. Woodward's (M)
is precisely the criterion that defines such an edge, and his "arrow-breaking"
intervention (I2) is the same operation as Pearl's do-operator (replacing the structural
assignment of X by a constant) — the two are mathematically aligned (Woodward's I-X-Y
graph = Pearl's intervened SCM). Thus PhysioMap inherits a coherent, manipulationist
content for "X causes Y" that is well-defined even in cyclic/feedback systems
(Woodward explicitly intends the account for the special sciences — biology, medicine —
where feedback and equilibrium are pervasive). This grounds why instantiating a
structural causal model (Pearl) gives PhysioMap edges genuine causal, not merely
associational, meaning.
