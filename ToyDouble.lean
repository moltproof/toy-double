module

-- Root module of the lemma library. Every lemma file under `ToyDouble/Lemmas/`
-- must be imported here with `public import` so that `lake build`, `Solution.lean`
-- and the audit see it.
public import ToyDouble.Lemmas.Basic
