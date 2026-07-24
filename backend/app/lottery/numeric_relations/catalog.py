"""Catálogo in-memory de Tabla 1 y Tabla 2 (1..100), estructuras separadas."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.lottery.numeric_relations.models import FormattedComputation
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


@dataclass
class TableCatalog:
    table1_rows: list[FormattedComputation] = field(default_factory=list)
    table2_rows: list[FormattedComputation] = field(default_factory=list)
    table1_number_to_code: dict[int, int] = field(default_factory=dict)
    table1_code_to_numbers: dict[int, list[int]] = field(default_factory=dict)
    table2_number_to_code: dict[int, int] = field(default_factory=dict)
    table2_code_to_numbers: dict[int, list[int]] = field(default_factory=dict)

    def get_table1_companions(self, mother_code: int) -> list[int]:
        return list(self.table1_code_to_numbers.get(int(mother_code), []))

    def get_table2_code_for_number(self, number: int) -> int:
        return self.table2_number_to_code[int(number)]

    def get_table2_neighbors(self, number: int, *, exclude_self: bool = True) -> list[int]:
        number = int(number)
        code = self.get_table2_code_for_number(number)
        group = list(self.table2_code_to_numbers.get(code, []))
        if exclude_self:
            return [x for x in group if x != number]
        return group


_CATALOG: TableCatalog | None = None


def build_catalog(*, force_rebuild: bool = False) -> TableCatalog:
    global _CATALOG
    if _CATALOG is not None and not force_rebuild:
        return _CATALOG

    t1 = generate_table1()
    t2 = generate_table2()
    cat = TableCatalog(
        table1_rows=t1,
        table2_rows=t2,
        table1_number_to_code={r.number: r.code for r in t1},
        table1_code_to_numbers=group_table1_by_code(t1),
        table2_number_to_code={r.number: r.code for r in t2},
        table2_code_to_numbers=group_table2_by_code(t2),
    )
    _CATALOG = cat
    return cat


def get_table1_companions(mother_code: int, catalog: TableCatalog | None = None) -> list[int]:
    return (catalog or build_catalog()).get_table1_companions(mother_code)


def get_table2_code_for_number(number: int, catalog: TableCatalog | None = None) -> int:
    return (catalog or build_catalog()).get_table2_code_for_number(number)


def get_table2_neighbors(
    number: int, *, exclude_self: bool = True, catalog: TableCatalog | None = None
) -> list[int]:
    return (catalog or build_catalog()).get_table2_neighbors(number, exclude_self=exclude_self)


__all__ = [
    "TableCatalog",
    "build_catalog",
    "calculate_table1_value",
    "calculate_table2_value",
    "format_table1_digits",
    "format_table2_digits",
    "generate_table1",
    "generate_table2",
    "group_table1_by_code",
    "group_table2_by_code",
    "get_table1_companions",
    "get_table2_code_for_number",
    "get_table2_neighbors",
]
