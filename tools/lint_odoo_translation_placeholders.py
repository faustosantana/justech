#!/usr/bin/env python3
"""Lint: detecta _() con placeholders nombrados mezclados con posicionales.

Uso:
  python3 tools/lint_odoo_translation_placeholders.py custom/
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

MIXED_RE = re.compile(
    r"""_\(\s*(['"])(?P<s>(?:\\.|(?!\1).)*)\1""",
    re.DOTALL,
)
NAMED = re.compile(r"%\([A-Za-z_][A-Za-z0-9_]*\)[#0\- +]*\d*(?:\.\d+)?[sdif]")
# Posicional estilo %.1f / %s / %d (no %% y no %(name)s)
POSITIONAL = re.compile(r"(?<!%)%(?!\()[#0\- +]*\d*(?:\.\d+)?[sdif]")


def check_file(path: Path) -> list[str]:
    issues = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{path}: read error {exc}"]
    for match in MIXED_RE.finditer(text):
        s = match.group("s")
        # unescape for analysis of %% 
        s_norm = s.replace("%%", "")
        has_named = bool(NAMED.search(s_norm))
        has_pos = bool(POSITIONAL.search(s_norm))
        if has_named and has_pos:
            line = text.count("\n", 0, match.start()) + 1
            issues.append(
                f"{path}:{line}: mixed named+positional placeholders in _(): {s[:120]!r}"
            )
    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("roots", nargs="+", type=Path)
    args = parser.parse_args()
    issues = []
    for root in args.roots:
        for path in root.rglob("*.py"):
            if "migrations" in path.parts and path.name.startswith("__"):
                continue
            issues.extend(check_file(path))
    for issue in issues:
        print(issue)
    if issues:
        print(f"FAIL: {len(issues)} issue(s)", file=sys.stderr)
        return 1
    print("PASS: no mixed translation placeholders")
    return 0


if __name__ == "__main__":
    sys.exit(main())
