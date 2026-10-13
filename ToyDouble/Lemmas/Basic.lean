module

public import Mathlib.Data.Nat.Basic

-- Add `@[expose]` to public definitions whose bodies downstream clients need.
public section

/-!
# Lemma library for `ToyDouble`

Agents add one file per blueprint node under `ToyDouble/Lemmas/` and import it
from `ToyDouble.lean` with `public import`. Every file is a Lean module: it
starts with `module`, imports with `public import` and keeps its declarations in
a `public section` so `Solution.lean` can use them. Each node's Lean declaration
name is recorded on the forum; the audit job reports which declarations are
sorry-free and which axioms they use. `Solution.lean` imports this library to
prove the advertised statement from `Challenge.lean`.
-/

namespace ToyDouble

end ToyDouble
