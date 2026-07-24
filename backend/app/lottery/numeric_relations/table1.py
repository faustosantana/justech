"""Tabla 1 — tabla madre: n ÷ 1220 → exactamente 11 dígitos (sin punto)."""

from __future__ import annotations

from decimal import Decimal

from app.lottery.numeric_relations.constants import DIVISOR, TABLE1_DECIMAL_PLACES, TABLE1_DIGIT_COUNT
from app.lottery.numeric_relations.decimal_math import (
    digits_without_point,
    format_fixed_decimals,
    sum_literal_digits,
    validate_n,
)
from app.lottery.numeric_relations.models import FormattedComputation, TableKind


def calculate_table1_value(n: int) -> Decimal:
    n = validate_n(n)
    return Decimal(n) / Decimal(DIVISOR)


def format_table1_digits(n: int) -> FormattedComputation:
    n = validate_n(n)
    raw = calculate_table1_value(n)
    visible = format_fixed_decimals(raw, TABLE1_DECIMAL_PLACES)
    digits = digits_without_point(visible)
    if len(digits) != TABLE1_DIGIT_COUNT:
        raise AssertionError(
            f"Tabla 1 n={n}: expected {TABLE1_DIGIT_COUNT} digits, got {len(digits)} ({visible!r})"
        )
    digit_list = tuple(int(ch) for ch in digits)
    code = sum_literal_digits(visible)
    return FormattedComputation(
        number=n,
        table=TableKind.TABLE_1,
        formula=f"{n} ÷ {DIVISOR}",
        visible_value=visible,
        digits_without_point=digits,
        digit_count=len(digits),
        digit_list=digit_list,
        code=code,
    )


def generate_table1() -> list[FormattedComputation]:
    from app.lottery.numeric_relations.constants import N_MAX, N_MIN

    return [format_table1_digits(n) for n in range(N_MIN, N_MAX + 1)]


def group_table1_by_code(
    rows: list[FormattedComputation] | None = None,
) -> dict[int, list[int]]:
    rows = rows if rows is not None else generate_table1()
    groups: dict[int, list[int]] = {}
    for row in rows:
        groups.setdefault(row.code, []).append(row.number)
    for code in groups:
        groups[code] = sorted(set(groups[code]))
    return dict(sorted(groups.items(), key=lambda kv: kv[0]))
