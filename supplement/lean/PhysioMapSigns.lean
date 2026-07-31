/-
  PhysioMap — Lean 4 formalization of the sign-solvability soundness core.
  Mathlib-free: uses only the Lean 4 core toolchain (Init).  No `sorry`.

  This mirrors `physiomap_core/qualitative.py`:

      _times       ↔  Sign.smul   (⊗, sign composition along a chain)
      _plus        ↔  Sign.sadd   (⊕, sign combination of parallel contributions)
      _neg         ↔  Sign.sneg
      _signed_det  ↔  SDet        (Laplace expansion, first available row,
                                    parity by position — identical recursion)

  `abstracts s z` says the integer `z` is a numerical realization consistent with the
  qualitative sign symbol `s` (plus↦positive, minus↦negative, zero↦0, unknown↦anything).

  ── What is PROVED (no axioms, no sorry) ──────────────────────────────────────
    smul_sound / sadd_sound / sneg_sound   the qualitative sign algebra is sound:
                                           each op abstracts the corresponding ℤ op.
    laplace_sound / SDet_sound             a definite sign-determinant is the sign of
                                           the determinant of EVERY sign-pattern-consistent
                                           integer matrix (general n).  This is exactly
                                           the guarantee behind the solver's numerator:
                                           `_signed_det` returns `?` on any term
                                           cancellation and is otherwise sound.
    committed_sign_sound                   the solver's committed comparative-static sign
                                           `_times(num, sign_det_j)` is sound — GIVEN the
                                           single classical fact below.

  ── The ONE classical fact NOT proved here (needs spectral theory / Mathlib) ───
    hurwitz_det_sign : a stable (Hurwitz) m×m Jacobian with negative diagonal has
    determinant sign (-1)^m.  This is the correspondence-principle step the solver uses
    (`qualitative.py:247`, `sign_det_j = + if m even else -`).  It is introduced as a
    SINGLE, clearly-labelled `axiom` (Samuelson 1947; Quirk–Ruppert 1965;
    Bassett, Maybee & Quirk 1968), not hidden as a `sorry`.
-/

namespace PhysioMap

/-! ## 1. The qualitative sign lattice -/

inductive Sign
  | plus | minus | zero | unknown
deriving DecidableEq, Repr

/-- `_times` (⊗): 0 absorbs to 0; then `?` absorbs to `?`; else the product of signs. -/
def Sign.smul : Sign → Sign → Sign
  | .zero, _ => .zero
  | _, .zero => .zero
  | .unknown, _ => .unknown
  | _, .unknown => .unknown
  | .plus, .plus => .plus
  | .plus, .minus => .minus
  | .minus, .plus => .minus
  | .minus, .minus => .plus

/-- `_plus` (⊕): 0 is the identity; `?` absorbs; agreeing signs combine; `+ ⊕ - = ?`. -/
def Sign.sadd : Sign → Sign → Sign
  | .zero, b => b
  | a, .zero => a
  | .unknown, _ => .unknown
  | _, .unknown => .unknown
  | .plus, .plus => .plus
  | .minus, .minus => .minus
  | .plus, .minus => .unknown
  | .minus, .plus => .unknown

/-- `_neg`. -/
def Sign.sneg : Sign → Sign
  | .plus => .minus
  | .minus => .plus
  | .zero => .zero
  | .unknown => .unknown

/-- Multiplicative identity of the sign semiring (`det [] = +1`). -/
def Sign.one : Sign := .plus
/-- Additive identity of the sign semiring. -/
def Sign.szero : Sign := .zero

/-! ## 2. Concretization: which integers a sign admits -/

/-- `abstracts s z`: the integer `z` is consistent with the sign symbol `s`. -/
def abstracts : Sign → Int → Prop
  | .plus, z => 0 < z
  | .minus, z => z < 0
  | .zero, z => z = 0
  | .unknown, _ => True

theorem abstracts_one : abstracts Sign.one 1 := by
  simp only [Sign.one, abstracts]; omega

theorem abstracts_szero : abstracts Sign.szero 0 := by
  simp only [Sign.szero, abstracts]

/-- Soundness of ⊗ against integer multiplication. -/
theorem smul_sound {sa sb : Sign} {a b : Int}
    (ha : abstracts sa a) (hb : abstracts sb b) :
    abstracts (sa.smul sb) (a * b) := by
  cases sa <;> cases sb <;>
    simp only [Sign.smul, abstracts] at ha hb ⊢ <;>
    first
      | trivial
      | (subst_vars; simp)
      | omega
      | exact Int.mul_pos ha hb
      | (have h := Int.mul_pos ha (show (0:Int) < -b by omega)
         rw [Int.mul_neg] at h; omega)
      | (have h := Int.mul_pos (show (0:Int) < -a by omega) hb
         rw [Int.neg_mul] at h; omega)
      | (have h := Int.mul_pos (show (0:Int) < -a by omega) (show (0:Int) < -b by omega)
         rw [Int.neg_mul, Int.mul_neg] at h; omega)

/-- Soundness of ⊕ against integer addition. -/
theorem sadd_sound {sa sb : Sign} {a b : Int}
    (ha : abstracts sa a) (hb : abstracts sb b) :
    abstracts (sa.sadd sb) (a + b) := by
  cases sa <;> cases sb <;>
    simp only [Sign.sadd, abstracts] at ha hb ⊢ <;>
    first | trivial | omega

/-- Soundness of sign negation against integer negation. -/
theorem sneg_sound {sa : Sign} {a : Int} (ha : abstracts sa a) :
    abstracts sa.sneg (-a) := by
  cases sa <;> simp only [Sign.sneg, abstracts] at ha ⊢ <;>
    first | trivial | omega

/-! ## 3. Laplace determinant, polymorphically, over a fuel argument

Both the sign determinant and the integer determinant are the SAME recursion — Laplace
expansion along the first available row, sign alternating by column position — differing
only in the underlying algebra.  A `fuel : Nat` argument (initialized to the matrix size)
makes the recursion structural, so termination is free and the soundness proof is a plain
induction on `fuel`. -/

/-- Every way to pick one element out of a list, tagged with the parity of its position
    (`false` = even).  Mirrors the `cols[:idx] + cols[idx+1:]` minor in `_signed_det`. -/
def picksP : List Nat → List (Bool × Nat × List Nat)
  | [] => []
  | x :: xs => (false, x, xs) :: (picksP xs).map (fun t => (!t.1, t.2.1, x :: t.2.2))

/-- Generic Laplace determinant over an algebra `(mul, add, neg, one, zero)`. -/
def laplace {α : Type} (mul add : α → α → α) (neg : α → α) (one zero : α)
    (E : Nat → Nat → α) : Nat → Nat → List Nat → α
  | 0, _, _ => one
  | _ + 1, _, [] => one
  | fuel + 1, row, x :: xs =>
      (picksP (x :: xs)).foldl
        (fun acc t =>
          add acc
            (mul (mul (E row t.2.1) (laplace mul add neg one zero E fuel (row + 1) t.2.2))
                 (if t.1 then neg one else one)))
        zero

/-- Sign determinant (mirrors `_signed_det`). -/
def laplaceS (S : Nat → Nat → Sign) : Nat → Nat → List Nat → Sign :=
  laplace Sign.smul Sign.sadd Sign.sneg Sign.one Sign.szero S

/-- Integer determinant by the identical recursion. -/
def laplaceZ (Z : Nat → Nat → Int) : Nat → Nat → List Nat → Int :=
  laplace (· * ·) (· + ·) (fun x => -x) (1 : Int) (0 : Int) Z

/-- Parity factor abstraction: `+1 ↦ plus`, `-1 ↦ minus`. -/
theorem abstracts_parity (b : Bool) :
    abstracts (if b then Sign.sneg Sign.one else Sign.one) (if b then -1 else 1) := by
  cases b <;> simp [Sign.one, Sign.sneg, abstracts] <;> omega

/-- Generic soundness of a left fold that combines with ⊕ / `+` term by term. -/
theorem foldl_sound {β : Type} (l : List β) (fS : β → Sign) (fZ : β → Int)
    (accS : Sign) (accZ : Int) (hacc : abstracts accS accZ)
    (hstep : ∀ t ∈ l, abstracts (fS t) (fZ t)) :
    abstracts (l.foldl (fun a t => Sign.sadd a (fS t)) accS)
              (l.foldl (fun a t => a + fZ t) accZ) := by
  induction l generalizing accS accZ with
  | nil => simpa using hacc
  | cons hd tl ih =>
    simp only [List.foldl_cons]
    apply ih
    · exact sadd_sound hacc (hstep hd (by simp))
    · intro t ht; exact hstep t (by simp [ht])

/-- **Determinant soundness (general n).**  If every entry sign abstracts the corresponding
    integer entry, then the sign determinant abstracts the integer determinant: a definite
    `laplaceS` result (`plus`/`minus`) is the sign of the integer determinant of every
    sign-pattern-consistent matrix. -/
theorem laplace_sound (S : Nat → Nat → Sign) (Z : Nat → Nat → Int)
    (H : ∀ r c, abstracts (S r c) (Z r c)) :
    ∀ fuel row cols, abstracts (laplaceS S fuel row cols) (laplaceZ Z fuel row cols) := by
  intro fuel
  induction fuel with
  | zero =>
    intro row cols
    simp only [laplaceS, laplaceZ, laplace]
    exact abstracts_one
  | succ f ih =>
    intro row cols
    cases cols with
    | nil =>
      simp only [laplaceS, laplaceZ, laplace]
      exact abstracts_one
    | cons x xs =>
      simp only [laplaceS, laplaceZ, laplace]
      apply foldl_sound (picksP (x :: xs))
        (fun t => Sign.smul (Sign.smul (S row t.2.1) (laplaceS S f (row + 1) t.2.2))
                            (if t.1 then Sign.sneg Sign.one else Sign.one))
        (fun t => Z row t.2.1 * laplaceZ Z f (row + 1) t.2.2 * (if t.1 then -1 else 1))
      · exact abstracts_szero
      · intro t _
        apply smul_sound
        · exact smul_sound (H row t.2.1) (ih (row + 1) t.2.2)
        · exact abstracts_parity t.1

/-! ## 4. The committed comparative-static sign -/

/-- Full sign determinant of an `m×m` sign matrix (`SDet S m`). -/
def SDet (S : Nat → Nat → Sign) (m : Nat) : Sign := laplaceS S m 0 (List.range m)
/-- Full integer determinant of an `m×m` integer matrix. -/
def IDet (Z : Nat → Nat → Int) (m : Nat) : Int := laplaceZ Z m 0 (List.range m)

/-- `SDet` is sound: a definite sign determinant is the determinant sign of every
    sign-consistent integer matrix. -/
theorem SDet_sound {S : Nat → Nat → Sign} {Z : Nat → Nat → Int} {m : Nat}
    (H : ∀ r c, abstracts (S r c) (Z r c)) : abstracts (SDet S m) (IDet Z m) :=
  laplace_sound S Z H m 0 (List.range m)

/-- An uninterpreted stability predicate.  We deliberately do NOT formalize Hurwitz
    stability (it needs eigenvalues / spectral theory); we only name the hypothesis under
    which the classical determinant-sign fact holds. -/
axiom StableNegDiag : (Nat → Nat → Int) → Nat → Prop

/-- **The one classical fact we do not prove** (needs spectral theory): a stable (Hurwitz)
    `m×m` Jacobian with negative diagonal has `sign(det J) = (-1)^m`.  This is exactly the
    correspondence-principle step the solver uses to pin the denominator sign for free
    (`qualitative.py:247`).  References: Samuelson, *Foundations of Economic Analysis*
    (1947); Quirk & Ruppert (1965); Bassett, Maybee & Quirk, *Qualitative economics and
    the scope of the correspondence principle*, Econometrica (1968). -/
axiom hurwitz_det_sign (m : Nat) (J : Nat → Nat → Int) (hstab : StableNegDiag J m) :
    abstracts (if m % 2 = 0 then Sign.plus else Sign.minus) (IDet J m)

/-- **Soundness of the committed comparative-static sign.**  The solver commits
    `_times(num, sign_det_j)` where `num = SDet` of the column-`i`-replaced matrix and
    `sign_det_j = (-1)^m` from stability.  This product is sound: it abstracts
    `det(J_i) · det(J)`, whose sign equals that of the comparative static
    `dx_i = det(J_i)/det(J)` (since `sign(1/det J) = sign(det J)`, noted in the paper).
    The numerator soundness is proved (`SDet_sound`); the denominator sign is the single
    axiom above. -/
theorem committed_sign_sound
    {m : Nat}
    {SJi : Nat → Nat → Sign} {ZJi : Nat → Nat → Int}   -- column-i-replaced matrix
    {ZJ : Nat → Nat → Int}                              -- the Jacobian itself
    (Hji : ∀ r c, abstracts (SJi r c) (ZJi r c))
    (hstab : StableNegDiag ZJ m) :
    abstracts (Sign.smul (SDet SJi m) (if m % 2 = 0 then Sign.plus else Sign.minus))
              (IDet ZJi m * IDet ZJ m) :=
  smul_sound (SDet_sound Hji) (hurwitz_det_sign m ZJ hstab)

end PhysioMap
