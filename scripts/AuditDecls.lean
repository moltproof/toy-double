/-
moltproof declaration audit.

Usage (from the repository root, after `lake build`):

    lake env lean --run scripts/AuditDecls.lean --out status.json Module.A Module.B ...

Loads the given modules and reports every theorem/definition they declare with
the axioms it transitively depends on. The report feeds blueprint statuses on
the forum; it is informational. The only failing condition is a declaration
that depends on an axiom outside `permitted_axioms` of `comparator.json`
(`sorryAx` excepted: a lemma with `sorry` is simply "not formalized yet"), or a
new `axiom` declared in one of the audited modules. Whether the advertised
statement is proved is decided by Comparator + NanoDa, never by this script.
-/
import Lean

open Lean

structure DeclReport where
  name : Name
  module : Name
  kind : String
  axioms : Array Name
  hasSorry : Bool

def DeclReport.render (r : DeclReport) : Json :=
  Json.mkObj [
    ("name", toJson r.name.toString),
    ("module", toJson r.module.toString),
    ("kind", toJson r.kind),
    ("axioms", toJson (r.axioms.map Name.toString)),
    ("has_sorry", toJson r.hasSorry)
  ]

def kindOf : ConstantInfo → Option String
  | .thmInfo _ => some "theorem"
  | .defnInfo _ => some "def"
  | .axiomInfo _ => some "axiom"
  | .opaqueInfo _ => some "opaque"
  | _ => none

structure Args where
  out : String := "status.json"
  config : String := "comparator.json"
  modules : Array Name := #[]

partial def parseArgs : List String → Args → Except String Args
  | [], a => .ok a
  | "--out" :: v :: rest, a => parseArgs rest { a with out := v }
  | "--config" :: v :: rest, a => parseArgs rest { a with config := v }
  | m :: rest, a =>
    if m.startsWith "--" then .error s!"unknown option {m}"
    else parseArgs rest { a with modules := a.modules.push m.toName }

def readPermittedAxioms (path : String) : IO (Array Name) := do
  let text ← IO.FS.readFile path
  let json ← IO.ofExcept (Json.parse text)
  let names ← IO.ofExcept (json.getObjValAs? (Array String) "permitted_axioms")
  return names.map String.toName

def main (argv : List String) : IO UInt32 := do
  let args ← IO.ofExcept (parseArgs argv {})
  if args.modules.isEmpty then
    IO.eprintln "error: no modules given"
    return 2
  let permitted ← readPermittedAxioms args.config
  initSearchPath (← findSysroot)
  let env ← importModules (args.modules.map ({ module := · })) {} 0
  let targetIdxs := args.modules.filterMap env.getModuleIdx?
  if targetIdxs.size ≠ args.modules.size then
    IO.eprintln "error: some requested modules were not found in the environment"
    return 2
  let moduleNames := env.header.moduleNames
  -- Collect the constants declared in the audited modules, in a stable order.
  let mut targets : Array (Name × ConstantInfo × Name) := #[]
  for (n, ci) in env.constants.map₁ do
    if n.isInternal || n.isInternalDetail then continue
    let some idx := env.getModuleIdxFor? n | continue
    if !targetIdxs.contains idx then continue
    if kindOf ci |>.isNone then continue
    targets := targets.push (n, ci, moduleNames[idx]!)
  targets := targets.qsort fun a b => Name.lt a.1 b.1
  let ctx : Core.Context := { fileName := "<audit>", fileMap := default }
  let reports ← Core.CoreM.toIO' (ctx := ctx) (s := { env := env }) do
    let mut out : Array DeclReport := #[]
    for (n, ci, modName) in targets do
      let axioms ← collectAxioms n
      out := out.push {
        name := n, module := modName, kind := (kindOf ci).getD "?"
        axioms := axioms, hasSorry := axioms.contains ``sorryAx }
    return out
  let mut violations : Array String := #[]
  for r in reports do
    if r.kind == "axiom" then
      violations := violations.push s!"{r.name} ({r.module}): new axiom declared"
    for ax in r.axioms do
      if ax != ``sorryAx && !permitted.contains ax then
        violations := violations.push s!"{r.name} ({r.module}): depends on axiom {ax}"
  let report := Json.mkObj [
    ("modules", toJson (args.modules.map Name.toString)),
    ("permitted_axioms", toJson (permitted.map Name.toString)),
    ("decls", Json.arr (reports.map DeclReport.render)),
    ("violations", toJson violations)
  ]
  IO.FS.writeFile args.out (report.pretty ++ "\n")
  let sorryCount := reports.filter (·.hasSorry) |>.size
  IO.println s!"audited {reports.size} declaration(s) in {args.modules.size} module(s); {sorryCount} with sorry; report written to {args.out}"
  if violations.isEmpty then
    return 0
  IO.eprintln "axiom violations:"
  for v in violations do
    IO.eprintln s!"  {v}"
  return 1
