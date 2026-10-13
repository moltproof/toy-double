#!/usr/bin/env python3
"""Unit tests for scripts/guard.py. Run with `python3 test/guard_test.py`."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("guard", ROOT / "scripts" / "guard.py")
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)

CONFIG = guard.load_config()


class StripCommentsTest(unittest.TestCase):
    def test_line_comment_removed(self):
        stripped = guard.strip_comments("a -- macro here\nb")
        self.assertEqual(stripped, "a" + " " * 14 + "\nb")

    def test_nested_block_comment_removed(self):
        code = "x /- outer /- inner macro -/ still comment -/ y"
        stripped = guard.strip_comments(code)
        self.assertNotIn("macro", stripped)
        self.assertTrue(stripped.startswith("x ") and stripped.endswith(" y"))

    def test_string_literal_removed(self):
        stripped = guard.strip_comments('have h := "run_cmd" ; exact h')
        self.assertNotIn("run_cmd", stripped)
        self.assertIn("exact h", stripped)

    def test_docstring_removed(self):
        stripped = guard.strip_comments("/-- uses native_decide -/\ntheorem t : True := trivial")
        self.assertNotIn("native_decide", stripped)
        self.assertIn("theorem t", stripped)


class TokenScanTest(unittest.TestCase):
    def scan(self, source: str, *, header: str = "module\n\n") -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "Agent.lean").write_text(header + source, encoding="utf-8")
            old_root = guard.ROOT
            guard.ROOT = root
            try:
                config = {"guard": {**CONFIG["guard"], "agent_paths": ["Agent.lean"]}}
                return [hit["token"] for hit in guard.scan_tokens(config)]
            finally:
                guard.ROOT = old_root

    def test_each_forbidden_token_is_caught(self):
        for token in CONFIG["guard"]["forbidden_tokens"]:
            with self.subTest(token=token):
                self.assertEqual(self.scan(f"theorem t : True := by\n  {token}\n"), [token])

    def test_code_running_commands_are_caught(self):
        self.assertEqual(self.scan("run_elab evil"), ["run_elab"])
        self.assertEqual(self.scan("theorem t : True := by_elab do evil"), ["by_elab"])
        self.assertEqual(self.scan("#eval! evil"), ["#eval"])

    def test_patterns_are_caught(self):
        self.assertEqual(self.scan("example : 2 + 2 = 4 := by decide +native"), ["decide +native"])
        self.assertEqual(self.scan("set_option debug.skipKernelTC true"), ["set_option debug."])
        self.assertEqual(self.scan("#eval IO.println 1"), ["#eval"])
        self.assertEqual(self.scan("#exit"), ["#exit"])

    def test_identifiers_containing_tokens_are_not_caught(self):
        clean = "\n".join(
            [
                "theorem macro_free (n : ℕ) : n = n := rfl",
                "theorem partial_order_lemma : True := trivial",
                "theorem elaborate : True := trivial",
                "theorem syntax_tree : True := trivial",
                "def unsafe_name : ℕ := 1",
                "example : 2 + 2 = 4 := by decide",
                "set_option maxHeartbeats 400000 in",
                "theorem Foo.axiom_free : True := trivial",
                "theorem uses_dot : True := Foo.axiom_free",
            ]
        )
        self.assertEqual(self.scan(clean), [])

    def test_module_header_is_required(self):
        missing = guard.MISSING_MODULE_HEADER
        self.assertEqual(self.scan("theorem t : True := trivial", header=""), [missing])
        self.assertEqual(self.scan("theorem t : True := trivial", header="import Mathlib\n"), [missing])
        # A documentation comment is a command, so it ends the header (Palomar's rule).
        self.assertEqual(self.scan("theorem t : True := trivial", header="/-! doc -/\nmodule\n"), [missing])
        self.assertEqual(self.scan("theorem t : True := trivial", header="-- note\n/- c -/\nmodule\n"), [])
        self.assertEqual(self.scan("theorem t : True := trivial", header="modules\n"), [missing])

    def test_module_syntax(self):
        allowed = "\n".join(
            [
                "public import Mathlib.Data.Nat.Basic",
                "import all Foo.Bar",
                "public section",
                "@[expose] public def double (n : ℕ) : ℕ := n + n",
                "theorem metaTheorem : True := trivial",
                "theorem uses_meta_name : True := Foo.meta_lemma",
                "end",
            ]
        )
        self.assertEqual(self.scan(allowed), [])
        for source in [
            "meta import Lean",
            "public meta import Lean",
            "meta def evil : IO Unit := pure ()",
            "public meta section",
            "@[command_elab Lean.Parser.Command.check] meta def e : Unit := ()",
        ]:
            with self.subTest(source=source):
                self.assertEqual(self.scan(source), ["meta"])

    def test_tokens_in_comments_are_ignored(self):
        self.assertEqual(self.scan("-- native_decide would be faster\ntheorem t : True := trivial"), [])

    def test_attribute_form_is_caught(self):
        self.assertEqual(self.scan("@[implemented_by fast] def slow : ℕ := 1"), ["implemented_by"])
        self.assertEqual(self.scan("@[extern \"c_fn\"] def f : ℕ := 1"), ["extern"])


class AgentPathTest(unittest.TestCase):
    def test_paths(self):
        agent_paths = ["Solution.lean", "Pkg.lean", "Pkg/"]
        self.assertTrue(guard.is_agent_path("Solution.lean", agent_paths))
        self.assertTrue(guard.is_agent_path("Pkg/Lemmas/Foo.lean", agent_paths))
        self.assertTrue(guard.is_agent_path("Pkg.lean", agent_paths))
        self.assertFalse(guard.is_agent_path("Challenge.lean", agent_paths))
        self.assertFalse(guard.is_agent_path("Pkg.lean.bak", agent_paths))
        self.assertFalse(guard.is_agent_path("PkgOther/Foo.lean", agent_paths))
        self.assertFalse(guard.is_agent_path(".github/workflows/ci.yml", agent_paths))
        self.assertFalse(guard.is_agent_path("comparator.json", agent_paths))


if __name__ == "__main__":
    unittest.main(verbosity=1)
