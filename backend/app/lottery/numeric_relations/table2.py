"""Tabla 2 — confirmación: 1220 ÷ n → exactamente 12 dígitos (sin punto)."""

from __future__ import annotations

from decimal import Decimal

from app.lottery.numeric_relations.constants import DIVISOR, TABLE2_DIGIT_COUNT
from app.lottery.numeric_relations.decimal_math import (
    digits_without_point,
    format_fixed_decimals,
    integer_digit_count,
    sum_literal_digits,
    validate_n,
)
from app.lottery.numeric_relations.models import FormattedComputation, TableKind


def calculate_table2_value(n: int) -> Decimal:
    n = validate_n(n)
    return Decimal(DIVISOR) / Decimal(n)


def format_table2_digits(n: int) -> FormattedComputation:
    n = validate_n(n)
    raw = calculate_table2_value(n)
    int_digits = integer_digit_count(raw)
    decimals = TABLE2_DIGIT_COUNT - int_digits
    if decimals < 0:
        raise AssertionError(f"Tabla 2 n={n}: integer digits {int_digits} exceed {TABLE2_DIGIT_COUNT}")
    visible = format_fixed_decimals(raw, decimals)
    digits = digits_without_point(visible)
    if len(digits) != TABLE2_DIGIT_COUNT:
        raise AssertionError(
            f"Tabla 2 n={n}: expected {TABLE2_DIGIT_COUNT} digits, got {len(digits)} ({visible!r})"
        )
    digit_list = tuple(int(ch) for ch in digits)
    code = sum_literal_digits(visible)
    return FormattedComputation(
        number=n,
        table=TableKind.TABLE_2,
        formula=f"{DIVISOR} ÷ {n}",
        visible_value=visible,
        digits_without_point=digits,
        digit_count=len(digits),
        digit_list=digit_list,
        code=code,
    )


def generate_table2() -> list[FormattedComputation]:
    from app.lottery.numeric_relations.constants import N_MAX, N_MIN

    return [format_table2_digits(n) for n in range(N_MIN, N_MAX + 1)]


def group_table2_by_code(
    rows: list[FormattedComputation] | None = None,
) -> dict[int, list[int]]:
    rows = rows if rows is not None else generate_table2()
    groups: dict[int, list[int]] = {}
    for row in rows:
        groups.setdefault(row.code, []).append(row.number)
    for code in groups:
        groups[code] = sorted(set(groups[code]))
    return dict(sorted(groups.items(), key=lambda kv: kv[0]))
