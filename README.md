# Toy double

A Lean 4 + Mathlib formalization. The statement lives in `Challenge.lean`, the
proof in `Solution.lean`; CI checks that the two match.

## Repository map

- `Challenge.lean` — the advertised statement, signed by the problem owner. Only
  the owner may change it.
- `Solution.lean` — the same declaration with its proof.
- `ToyDouble/Lemmas/` — the lemma library; one file per blueprint node.
  Every Lean file is a module (`module` header, `public import`,
  `public section`), as Palomar requires.
- `comparator.json` — which declarations Comparator must match.
- `formalization.yaml` — Palomar metadata.
- `moltproof.toml` — guard and audit configuration read by CI.
- `docbuild/` — the doc-gen4 project for the API documentation.
- `scripts/verify-comparator.sh` — runs the `lake comparator` that ships in
  the pinned toolchain, with its bundled NanoDa and con-ron kernels, under
  bubblewrap, exactly as Palomar does.
- `scripts/check-lean-sources.py` — Palomar's source requirements (module
  header, at most 10,000 lines per file), checked before every build.

## How CI decides

1. `build` — Palomar's source check, then `lake build` with the pinned
   Mathlib.
2. `guard` — refuses proof files without the `module` header or with forbidden
   tokens, and labels pull requests that touch protected paths as
   `needs-owner-review`.
3. `audit` — `leanchecker` over the lemma modules (`--fresh` on `Solution`,
   which re-checks Mathlib too) and a declaration report (`status.json`).
4. `comparator` — `lake comparator` with the Lean, NanoDa and con-ron kernels
   checks that `Solution.lean` proves exactly the statement in `Challenge.lean`
   with the permitted axioms. Green on `main` means the problem is solved.
5. `docs` — doc-gen4 API documentation (informational).
6. `automerge` — merges pull requests from the maintenance bot once 1–3 (and
   the Palomar metadata checks) are green; neither `comparator` nor `docs`
   gates it.

## Working locally

```text
lake exe cache get
lake build
ruby scripts/validate-formalization.rb
(cd docbuild && lake build ToyDouble:docs)
./scripts/verify-comparator.sh   # Linux only (needs bwrap)
```

## Palomar

When `comparator` is green on `main`, the repository is ready to be submitted to
the [Palomar registry](https://palomar-registry.org/) through
[the submission form](https://submit.palomar-registry.org/) with the full
commit SHA of that run.
