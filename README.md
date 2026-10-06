# Toy double

A Lean 4 + Mathlib formalization. The statement lives in `Challenge.lean`, the
proof in `Solution.lean`; CI checks that the two match.

## Repository map

- `Challenge.lean` — the advertised statement, signed by the problem owner. Only
  the owner may change it.
- `Solution.lean` — the same declaration with its proof.
- `ToyDouble/Lemmas/` — the lemma library; one file per blueprint node.
- `comparator.json` — which declarations Comparator must match.
- `formalization.yaml` — Palomar metadata.
- `moltproof.toml` — guard and audit configuration read by CI.
- `scripts/verify-comparator.sh` — pinned Comparator, lean4export, NanoDa and
  Landrun revisions; `scripts/landrun-wrapper.sh` keeps the sandbox intact.

## How CI decides

1. `build` — `lake build` with the pinned Mathlib.
2. `guard` — refuses forbidden tokens in proof files and labels pull requests
   that touch protected paths as `needs-owner-review`.
3. `audit` — `leanchecker` over the lemma modules (`--fresh` on `Solution`,
   which re-checks Mathlib too) and a declaration report (`status.json`).
4. `comparator` — Comparator + NanoDa check that `Solution.lean` proves exactly
   the statement in `Challenge.lean` with the permitted axioms. Green on `main`
   means the problem is solved.
5. `automerge` — merges pull requests from the maintenance bot once 1–3 are
   green.

## Working locally

```text
lake exe cache get
lake build
ruby scripts/validate-formalization.rb
./scripts/verify-comparator.sh   # Linux only (Landrun)
```

## Palomar

When `comparator` is green on `main`, the repository is ready to be submitted to
the [Palomar registry](https://palomar-registry.org/) through
[the submission form](https://submit.palomar-registry.org/) with the full
commit SHA of that run.
