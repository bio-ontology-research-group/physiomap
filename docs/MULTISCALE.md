# PhysioMap content and semantics

PhysioMap v1.1.1 represents physiological traits as quantitative endogenous
random variables in a structural causal model. The resource is not a signed
graph. Derivative signs are a qualitative abstraction derived from the
quantitative semantics.

## Quantitative model

Let \(X=(X_1,\ldots,X_n)\) denote the endogenous trait variables and \(U\)
the exogenous variables. Their differentiable dynamics are

\[
\dot{x}_i=F_i(x_i,x_{\operatorname{pa}(i)},U_i).
\]

The current qualitative solver concerns local changes around a locally unique,
stable equilibrium \(x^\ast\). A perfect intervention on a variable replaces
that variable's mechanism or defining equation and leaves the remaining
equations unchanged.

The five PhysioMap content relation types impose different constraints on this
quantitative model.

| Relation type | Quantitative constraint |
|---|---|
| causal influence | The target mechanism depends non-constantly on the source variable. An optional sign constrains the sign of the corresponding partial derivative. |
| production | A process contributes a signed production or removal term to the mechanism of its output. |
| constitution | A variable of a whole is a function of variables of its constituents. |
| quantitative identity | A named variable equals a specified function of its arguments. |
| modulation | A modulator constrains how the derivative of a target mechanism with respect to a source variable changes. |

These types are not interchangeable. In particular, constitution and
quantitative identity are directed defining constraints. Intervening on the
result replaces its defining equation and does not propagate backward to the
arguments.

Scale is descriptive rather than semantic. A relation can connect molecular,
cellular, tissue, organ, organ-system, or whole-body variables, but its type is
determined by the constraint it states, not by the scales of its endpoints.

## Derivative-sign abstraction

For a causal influence from source \(X_s\) to target \(X_t\), define

\[
\sigma_{st} =
\operatorname{sign}\left(\frac{\partial F_t}{\partial x_s}\right).
\]

The values `+` and `-` constrain the local derivative sign. The value `?`
asserts non-constant direct dependence without fixing that sign. It is a
derivative-sign value, not a value taken by either random variable.

Production relations and quantitative identities can also supply derivative
signs for their arguments. The first-order solver projects those compatible
derivatives into one operational Jacobian while retaining their canonical
relation types in PhysioMap.

A modulation is second order. For modulator \(X_m\), source \(X_s\), and
target \(X_t\), its sign constrains

\[
\operatorname{sign}\left(
\frac{\partial^2 F_t}{\partial x_m\,\partial x_s}
\right).
\]

The first-order endpoint solver does not treat modulation as another causal
influence. A separate gain-sensitivity query uses the modulation constraint to
report whether a direct effect becomes more or less positive.

## Feedback-aware intervention solver

For a local intervention parameter \(\theta\), the implicit function theorem
gives the equilibrium response

\[
\frac{d x^\ast}{d\theta}
=
-\left(\frac{\partial F}{\partial x}\right)^{-1}
\frac{\partial F}{\partial\theta}.
\]

The solver evaluates the sign of this expression from the derivative-sign
abstraction. It returns `+` or `-` only when every admissible quantitative
realization has that sign, and returns `?` when the available constraints do
not determine it.

Exact signed-determinant expansion is exponential in the size of a feedback
component. The default exact cutoff is 16 traits. Larger components use a
conservative approximation. This is a configurable computational limit, not a
semantic boundary or a fitted value.

PhysioMap v1.1.1 includes nine exact quantitative identities, but it does not
provide complete functions, parameters, or exogenous distributions for the
whole resource. Therefore, the released solver evaluates derivative signs
rather than numerical effect sizes or population distributions.

## Content versus construction evidence

The five relation types above constitute PhysioMap content. Evidence and
provenance are metadata attached to each projected axiom. They document why an
axiom was admitted and where it came from, but they are not additional content
types and are not inputs to the solver.

For causal influences, the released evidence model distinguishes
interventional support from mechanistic support:

- interventional evidence comprises genetic loss- or gain-of-function,
  pharmacological, and perturbation evidence;
- mechanistic evidence comprises curated mechanistic statements and
  mechanistic models;
- unclassified legacy evidence remains explicit rather than being relabeled
  without review.

The evidence model was used to construct and audit PhysioMap. The current
content review is documented in
[`EXPERT_GOLD_REVIEW.md`](EXPERT_GOLD_REVIEW.md).

## Canonical artifacts

The authoritative OWL knowledge base is
[`release/owl-scm/physiomap.owl`](../release/owl-scm/physiomap.owl). The
versioned projection rules are
[`projection/patterns.yaml`](../projection/patterns.yaml), and their canonical
structural causal model projection is
[`release/owl-scm/physiomap-scm.json`](../release/owl-scm/physiomap-scm.json).
