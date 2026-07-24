"""Fachada del Motor de Relaciones Numéricas (Fases A+B)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from app.lottery.numeric_relations.analysis import analyze_observed_number
from app.lottery.numeric_relations.catalog import TableCatalog, build_catalog
from app.lottery.numeric_relations.history import DrawHistoryPort
from app.lottery.numeric_relations.models import AnalysisResult, OccurrenceLimit
from app.lottery.numeric_relations.table1 import (
    calculate_table1_value,
    format_table1_digits,
    generate_table1,
    group_table1_by_code,
)
from app.lottery.numeric_relations.table2 import (
    calculate_table2_value,
    format_table2_digits,
    generate_table2,
    group_table2_by_code,
)


class NumericRelationsService:
    def __init__(
        self,
        *,
        history: DrawHistoryPort | None = None,
        catalog: TableCatalog | None = None,
    ) -> None:
        self._history = history
        self._catalog = catalog or build_catalog()

    @property
    def catalog(self) -> TableCatalog:
        return self._catalog

    def comparative_table(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for r1, r2 in zip(self._catalog.table1_rows, self._catalog.table2_rows):
            rows.append(
                {
                    "number": r1.number,
                    "table1_visible": r1.visible_value,
                    "table1_digits": r1.digits_without_point,
                    "table1_code": r1.code,
                    "table2_visible": r2.visible_value,
                    "table2_digits": r2.digits_without_point,
                    "table2_code": r2.code,
                }
            )
        return rows

    def analyze(
        self,
        observed_number: int,
        lottery_ids: list[UUID | str],
        occurrence_limit: OccurrenceLimit,
        *,
        lottery_names: dict[str, str] | None = None,
    ) -> AnalysisResult:
        if self._history is None:
            raise RuntimeError("DrawHistoryPort is required for analysis")
        return analyze_observed_number(
            observed_number,
            lottery_ids,
            occurrence_limit,
            history=self._history,
            catalog=self._catalog,
            lottery_names=lottery_names,
        )

    def export_artifacts(self, out_dir: Path) -> dict[str, Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        paths: dict[str, Path] = {}

        comparative = self.comparative_table()
        p = out_dir / "comparative_table_1_to_100.json"
        p.write_text(json.dumps(comparative, ensure_ascii=False, indent=2), encoding="utf-8")
        paths["comparative"] = p

        g1 = {str(k): v for k, v in self._catalog.table1_code_to_numbers.items()}
        p = out_dir / "table1_groups.json"
        p.write_text(json.dumps(g1, ensure_ascii=False, indent=2), encoding="utf-8")
        paths["table1_groups"] = p

        g2 = {str(k): v for k, v in self._catalog.table2_code_to_numbers.items()}
        p = out_dir / "table2_groups.json"
        p.write_text(json.dumps(g2, ensure_ascii=False, indent=2), encoding="utf-8")
        paths["table2_groups"] = p

        # Markdown comparative (compact)
        md_lines = [
            "# Tabla comparativa Motor Relaciones Numéricas (1..100)",
            "",
            "| n | Tabla1 visible | T1 dígitos | T1 código | Tabla2 visible | T2 dígitos | T2 código |",
            "|---:|---|---|---:|---|---|---:|",
        ]
        for row in comparative:
            md_lines.append(
                f"| {row['number']} | {row['table1_visible']} | `{row['table1_digits']}` | {row['table1_code']} "
                f"| {row['table2_visible']} | `{row['table2_digits']}` | {row['table2_code']} |"
            )
        p = out_dir / "COMPARATIVE_TABLE_1_100.md"
        p.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
        paths["comparative_md"] = p

        return paths


__all__ = [
    "NumericRelationsService",
    "OccurrenceLimit",
    "build_catalog",
    "calculate_table1_value",
    "calculate_table2_value",
    "format_table1_digits",
    "format_table2_digits",
    "generate_table1",
    "generate_table2",
    "group_table1_by_code",
    "group_table2_by_code",
    "analyze_observed_number",
]
