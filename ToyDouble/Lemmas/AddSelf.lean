module

public import Mathlib.Data.Nat.Basic

public section

namespace ToyDouble

theorem add_self_eq_two_mul (n : ℕ) : n + n = 2 * n := by
  exact (Nat.two_mul n).symm

end ToyDouble
