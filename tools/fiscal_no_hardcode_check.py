#!/usr/bin/env python3
"""
Validador anti-hardcode para módulos fiscales Justech.

Escanea custom/justech_l10n_do_* en busca de referencias a clientes,
empresas, RNC, bancos, diarios, cuentas o secuencias fijas.

Uso:
    python3 tools/fiscal_no_hardcode_check.py [--path custom] [--strict]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCAN = ROOT / "custom"

SKIP_DIRS = {".git", "__pycache__", "static", "i18n", "diagrams", "tests"}
SKIP_SUFFIXES = {".png", ".jpg", ".pdf", ".docx", ".xlsx", ".pyc", ".po", ".pot"}
ALLOWLIST_FILES = {
    "README.md",
    "CHANGELOG.md",
    "ARCHITECTURE.md",
    "MIGRATION.md",
    "ROADMAP.md",
    "fiscal_no_hardcode_check.py",
}

RULES: list[tuple[str, re.Pattern[str], str]] = [
    (
        "client_reference",
        re.compile(r"\bhellenia\b|\badel\b|\bqlogistic\b|\bjustgroup\b", re.I),
        "Referencia a cliente/legacy no permitida en código producto.",
    ),
    (
        "rnc_literal",
        re.compile(r"(?<![\w.])(?:1[0-3]\d{7}|13[0-2]\d{7})(?![\w.])"),
        "Posible RNC hardcodeado (9 dígitos típicos DGII).",
    ),
    (
        "bank_name",
        re.compile(
            r"\b(banco\s+(popular|bhd|reservas|santa\s+cr[úu]z|scotiabank)|"
            r"banreservas|bpd)\b",
            re.I,
        ),
        "Nombre de banco hardcodeado.",
    ),
    (
        "journal_code",
        re.compile(
            r"""['"](?:INV|BILL|BNK1|BNK2|CASH|SLR|PRV|VTA|COM)['"]"""
        ),
        "Código de diario hardcodeado.",
    ),
    (
        "account_code",
        re.compile(r"""['"](?:[1-689]\d{5,})['"]"""),
        "Posible código de cuenta contable hardcodeado.",
    ),
    (
        "sequence_literal",
        re.compile(
            r"ir\.sequence[^;\n]{0,80}['\"][a-z0-9_.-]+(?:ncf|invoice|seq)[a-z0-9_.-]*['\"]",
            re.I,
        ),
        "Referencia a secuencia fija.",
    ),
]

ALLOWLIST_LINE_PATTERNS = [
    re.compile(r"anti-hardcode|no_hardcode|fiscal_no_hardcode", re.I),
    re.compile(r"example|ejemplo|placeholder|TODO Sprint", re.I),
    re.compile(r"B0100000001|B0200000001"),  # NCF de ejemplo en tests/docs
    re.compile(r"doc_type_b0[0-9]"),  # xml ids estándar DGII
    re.compile(r"https?://"),
]


def should_scan(path: Path) -> bool:
    if path.name in ALLOWLIST_FILES:
        return False
    if path.suffix.lower() in SKIP_SUFFIXES:
        return False
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    return path.suffix in {".py", ".xml", ".js", ".scss", ".csv", ".yaml", ".yml", ".md"}


def line_allowed(line: str) -> bool:
    return any(p.search(line) for p in ALLOWLIST_LINE_PATTERNS)


def scan_file(path: Path) -> list[dict]:
    findings: list[dict] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return findings
    rel = path.relative_to(ROOT)
    for lineno, line in enumerate(text.splitlines(), start=1):
        if line_allowed(line):
            continue
        for rule_id, pattern, message in RULES:
            if pattern.search(line):
                findings.append(
                    {
                        "file": str(rel),
                        "line": lineno,
                        "rule": rule_id,
                        "message": message,
                        "snippet": line.strip()[:120],
                    }
                )
    return findings


def iter_module_paths(base: Path) -> list[Path]:
    modules = sorted(base.glob("justech_l10n_do_*"))
    return [m for m in modules if m.is_dir()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Justech fiscal anti-hardcode checker")
    parser.add_argument("--path", type=Path, default=DEFAULT_SCAN)
    parser.add_argument("--strict", action="store_true", help="Exit 1 on any finding")
    args = parser.parse_args()

    all_findings: list[dict] = []
    for module in iter_module_paths(args.path):
        for file_path in module.rglob("*"):
            if file_path.is_file() and should_scan(file_path):
                all_findings.extend(scan_file(file_path))

    if not all_findings:
        print("OK — no hardcode findings in justech_l10n_do_* modules.")
        return 0

    print(f"WARN — {len(all_findings)} finding(s):\n")
    for item in all_findings:
        print(
            f"  [{item['rule']}] {item['file']}:{item['line']} — {item['message']}\n"
            f"    {item['snippet']}\n"
        )

    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
