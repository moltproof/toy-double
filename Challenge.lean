import Mathlib.Data.Nat.Basic

/-!
# Advertised statement

Toy problem used to exercise the moltproof pipeline end to end: doubling a
natural number by addition agrees with multiplication by two.
-/

/-- Adding a natural number to itself equals multiplying it by two. -/
theorem ToyDouble.main_result (n : ℕ) : n + n = 2 * n := by
  sorry
