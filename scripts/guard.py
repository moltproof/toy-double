#!/usr/bin/env python3
"""moltproof guard: keep agent pull requests inside their sandbox.

Two checks, selected by subcommand:

  paths  --base <ref>   list changed files outside `guard.agent_paths`
                        (exit 3 when any protected path was touched)
  tokens                scan agent-editable Lean files for forbidden tokens
                        and patterns (exit 1 on any hit)

Configuration comes from `moltproof.toml` at the repository root. Only the
Python standard library is used so the script runs on a bare GitHub runner.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "moltproof.toml"


def load_config() -> dict:
    with CONFIG_PATH.open("rb") as handle:
        return tomllib.load(handle)


def is_agent_path(path: str, agent_paths: list[str]) -> bool:
    for allowed in agent_paths:
        if allowed.endswith("/"):
            if path.startswith(allowed):
                return True
        elif path == allowed:
            return True
    return False


def changed_files(base: str) -> list[str]:
    output = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACDMRT", f"{base}...HEAD"],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT,
    ).stdout
    return [line.strip() for line in output.splitlines() if line.strip()]


def strip_comments(source: str) -> str:
    """Remove Lean line comments, nested block comments and string literals.

    Tokens inside comments or strings are not code, so they must not trigger
    the forbidden-token check. The removed spans are replaced by spaces to
    keep word boundaries intact.
    """
    out: list[str] = []
    i = 0
    n = len(source)
    depth = 0
    while i < n:
        two = source[i : i + 2]
        if depth > 0:
            if two == "/-":
                depth += 1
                i += 2
            elif two == "-/":
                depth -= 1
                i += 2
            else:
                out.append("\n" if source[i] == "\n" else " ")
                i += 1
            continue
        if two == "/-":
            depth = 1
            i += 2
            continue
        if two == "--":
            end = source.find("\n", i)
            end = n if end == -1 else end
            out.append(" " * (end - i))
            i = end
            continue
        if source[i] == '"':
            j = i + 1
            while j < n and source[j] != '"':
                j += 2 if source[j] == "\\" else 1
            out.append(" " * (min(j + 1, n) - i))
            i = j + 1
            continue
        out.append(source[i])
        i += 1
    return "".join(out)


def agent_lean_files(agent_paths: list[str]) -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for allowed in agent_paths:
        target = ROOT / allowed
        if allowed.endswith("/"):
            files.extend(sorted(target.rglob("*.lean")))
        elif target.exists() and target.suffix == ".lean":
            files.append(target)
    return files


def find_forbidden(source: str, tokens: list[str], patterns: list[str]) -> list[tuple[int, str]]:
    """Return (line, token) pairs for every forbidden token or pattern in Lean source."""
    token_regex = re.compile(
        r"(?<![A-Za-z0-9_.'!?])(" + "|".join(map(re.escape, tokens)) + r")(?![A-Za-z0-9_'!?])"
    )
    compiled = [re.compile(p) for p in patterns]
    hits: list[tuple[int, str]] = []
    code = strip_comments(source)
    for lineno, line in enumerate(code.splitlines(), 1):
        for match in token_regex.finditer(line):
            hits.append((lineno, match.group(1)))
        for pattern in compiled:
            for match in pattern.finditer(line):
                hits.append((lineno, match.group(0)))
    return hits


def scan_tokens(config: dict) -> list[dict]:
    guard = config["guard"]
    hits: list[dict] = []
    for path in agent_lean_files(guard["agent_paths"]):
        for lineno, token in find_forbidden(
            path.read_text(encoding="utf-8"), guard["forbidden_tokens"], guard.get("forbidden_patterns", [])
        ):
            hits.append({"file": str(path.relative_to(ROOT)), "line": lineno, "token": token})
    return hits


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    paths = sub.add_parser("paths", help="report changed files outside agent paths")
    paths.add_argument("--base", required=True, help="base ref of the pull request")
    paths.add_argument("--json", action="store_true", help="print a JSON report")
    tokens = sub.add_parser("tokens", help="scan agent files for forbidden tokens")
    tokens.add_argument("--json", action="store_true", help="print a JSON report")
    args = parser.parse_args(argv)

    config = load_config()
    agent_paths = config["guard"]["agent_paths"]

    if args.command == "paths":
        changed = changed_files(args.base)
        protected = [path for path in changed if not is_agent_path(path, agent_paths)]
        if args.json:
            print(json.dumps({"changed": changed, "protected": protected}))
        elif protected:
            print("protected paths changed (needs owner review):")
            for path in protected:
                print(f"  {path}")
        else:
            print(f"all {len(changed)} changed file(s) are agent-editable")
        return 3 if protected else 0

    hits = scan_tokens(config)
    if args.json:
        print(json.dumps({"hits": hits}))
    elif hits:
        print("forbidden tokens found in agent files:")
        for hit in hits:
            print(f"  {hit['file']}:{hit['line']}: {hit['token']}")
    else:
        print("no forbidden tokens in agent files")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
