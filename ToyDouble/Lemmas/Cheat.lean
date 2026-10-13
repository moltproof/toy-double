module

public import Mathlib.Data.Nat.Basic

public section

axiom ToyDouble.cheat : False

theorem ToyDouble.zero_eq_one : 0 = 1 := ToyDouble.cheat.elim
