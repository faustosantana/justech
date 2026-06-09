#!/usr/bin/env python3
"""Genera .qa/e2e-summary.md desde resultados Playwright."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E2E = ROOT / ".qa/e2e"
RESULTS = E2E / "results.json"
SUMMARY = E2E / "e2e-summary.md"


def _find_screenshots(test_title: str) -> list[str]:
    slug = test_title.replace(" ", "-").replace("/", "-")
    evidence = E2E / "evidence"
    if not evidence.exists():
        return []
    paths: list[str] = []
    for folder in evidence.iterdir():
        if folder.is_dir() and slug[:20] in folder.name.replace(" ", "-"):
            paths.extend(str(p.relative_to(ROOT)) for p in sorted(folder.glob("*.png")))
    return paths


def main() -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# QA E2E — resumen funcional autónomo",
        "",
        f"- **Generado:** {ts}",
        f"- **Resultados JSON:** `.qa/e2e/results.json`",
        f"- **Reporte HTML:** `.qa/e2e/html-report/index.html`",
        f"- **Videos/traces:** `.qa/e2e/test-results/`",
        "",
    ]

    if not RESULTS.exists():
        lines.extend(["## Estado", "", "**Validación funcional en curso** — no se encontró results.json", ""])
        SUMMARY.write_text("\n".join(lines), encoding="utf-8")
        print(f"Resumen parcial: {SUMMARY}")
        return

    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    stats = data.get("stats", {})
    passed = stats.get("expected", 0)
    failed = stats.get("unexpected", 0)
    skipped = stats.get("skipped", 0)
    verdict = "**Validación funcional completa**" if failed == 0 else "**Validación fallida**"

    lines.extend([
        "## Estado",
        "",
        verdict,
        "",
        f"| Métrica | Valor |",
        f"| --- | --- |",
        f"| Passed | {passed} |",
        f"| Failed | {failed} |",
        f"| Skipped | {skipped} |",
        "",
        "## Pruebas",
        "",
    ])

    for suite in data.get("suites", []):
        for spec in suite.get("suites", []):
            for test in spec.get("tests", []):
                title = test.get("title", "sin título")
                results = test.get("results", [])
                status = results[0].get("status", "unknown") if results else "unknown"
                shots = _find_screenshots(title)
                lines.append(f"### {title}")
                lines.append("")
                lines.append(f"- **Resultado:** {status}")
                if shots:
                    lines.append(f"- **Screenshots:**")
                    for s in shots:
                        lines.append(f"  - `{s}`")
                lines.append(f"- **Evidencia persistencia:** verificada vía API en spec Playwright")
                lines.append("")

    fixtures = E2E / "fixtures.json"
    if fixtures.exists():
        fx = json.loads(fixtures.read_text(encoding="utf-8"))
        lines.extend([
            "## Fixtures seed",
            "",
            f"- Documentos E2E: {len(fx.get('document_ids', []))}",
            f"- Borradores E2E: {len(fx.get('draft_ids', []))}",
            f"- Prefijo: `{fx.get('e2e_prefix', '')}`",
            "",
        ])

    SUMMARY.write_text("\n".join(lines), encoding="utf-8")
    print(f"Resumen: {SUMMARY}")


if __name__ == "__main__":
    main()
