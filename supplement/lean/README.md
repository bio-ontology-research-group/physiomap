# PhysioMap — machine-checked soundness of the sign-solvability core

This directory contains a **Mathlib-free Lean 4** formalization of the soundness argument
behind PhysioMap's qualitative comparative-statics solver
(`physiomap_core/qualitative.py`). It compiles against the Lean 4 core toolchain alone —
no Mathlib, no network — in a couple of seconds.

## What is machine-checked

The file [`PhysioMapSigns.lean`](PhysioMapSigns.lean) mirrors the solver's sign algebra
exactly and proves it sound with respect to integer arithmetic. `abstracts s z` means the
integer `z` is a numerical realization consistent with the qualitative sign symbol `s`
(`plus ↦ z>0`, `minus ↦ z<0`, `zero ↦ z=0`, `unknown ↦ anything`).

| Lean name | Statement | Mirrors |
|---|---|---|
| `smul_sound` | `abstracts sa a → abstracts sb b → abstracts (sa.smul sb) (a*b)` | `_times` (⊗) |
| `sadd_sound` | `abstracts sa a → abstracts sb b → abstracts (sa.sadd sb) (a+b)` | `_plus` (⊕) |
| `sneg_sound` | `abstracts sa a → abstracts sa.sneg (-a)` | `_neg` |
| `laplace_sound` | for all `fuel row cols`, if every entry sign abstracts its integer entry then `laplaceS` abstracts `laplaceZ` | `_signed_det` |
| `SDet_sound` | `(∀ r c, abstracts (S r c) (Z r c)) → abstracts (SDet S m) (IDet Z m)` | full determinant |
| `committed_sign_sound` | the solver's committed sign `_times(num, sign_det_j)` abstracts `det(J_i)·det(J)` | `_solve_scc_exact` |

**Headline result — `SDet_sound`.** The sign determinant (`SDet`, a Laplace expansion that
returns `unknown` on any term cancellation, exactly like `_signed_det`) is a *sound
abstraction* of the integer determinant: whenever it returns a definite sign (`plus`/`minus`),
**every** integer matrix consistent with the sign pattern has a determinant of that sign.
This is the guarantee behind the numerator of the Cramer ratio the solver commits to. Proved
for **general `n`** (Laplace expansion made structurally recursive via a `fuel` argument, so
termination is free and soundness is a plain induction on `fuel`).

## The one thing that is *axiomatized*, and why

The solver pins the **denominator** sign of the Cramer ratio for free using the
correspondence principle: a stable (Hurwitz) `m×m` Jacobian with negative diagonal has
`sign(det J) = (-1)^m` (`qualitative.py:247`, `sign_det_j = + if m even else -`). That fact
needs spectral theory (the determinant is the product of eigenvalues, which come in complex
conjugate pairs), which is out of reach without Mathlib. It is therefore introduced as a
**single, clearly-labelled `axiom`**:

```lean
axiom hurwitz_det_sign (m : Nat) (J : Nat → Nat → Int) (hstab : StableNegDiag J m) :
    abstracts (if m % 2 = 0 then Sign.plus else Sign.minus) (IDet J m)
```

`StableNegDiag` is an uninterpreted predicate (we name the stability hypothesis without
formalizing Hurwitz stability itself). References: Samuelson, *Foundations of Economic
Analysis* (1947); Quirk & Ruppert (1965); Bassett, Maybee & Quirk, *Qualitative economics
and the scope of the correspondence principle*, Econometrica (1968).

`committed_sign_sound` then shows the solver's committed sign is sound **given** this axiom:
the proved `SDet_sound` handles the numerator, the axiom handles the denominator, and
`smul_sound` combines them — matching `_times(num, sign_det_j)` in the code.

## Honesty guarantees (checked, not asserted)

- **No `sorry`, no `admit`** anywhere in the proofs.
- **Axiom audit** (`#print axioms`):
  - `laplace_sound`, `SDet_sound` depend on `[propext, Quot.sound]` only — the Lean core
    axioms. No custom axioms, no `sorryAx`, not even `Classical.choice`.
  - `committed_sign_sound` depends on `[propext, StableNegDiag, hurwitz_det_sign, Quot.sound]`
    — i.e. only the two intended, labelled axioms on top of Lean core.

## Reproducing the build

Toolchain is pinned in [`lean-toolchain`](lean-toolchain): **`leanprover/lean4:v4.30.0`**
(managed by `elan`; no other dependencies).

```bash
# Option A — direct (fastest):
lean PhysioMapSigns.lean          # exit 0, no output = success

# Option B — via lake:
lake build                        # "Build completed successfully"
```

To re-run the axiom audit:

```bash
echo 'import PhysioMapSigns
open PhysioMap
#print axioms laplace_sound
#print axioms committed_sign_sound' > _check.lean
lake build && LEAN_PATH="$PWD/.lake/build/lib/lean" lean _check.lean
rm _check.lean
```
