"""Fase A — Tabla 2: ejemplos documentales + 1..100."""

from __future__ import annotations

from decimal import Decimal

from app.lottery.numeric_relations.constants import TABLE2_DIGIT_COUNT
from app.lottery.numeric_relations.table2 import (
    calculate_table2_value,
    format_table2_digits,
    generate_table2,
)


def test_table2_example_1():
    row = format_table2_digits(1)
    assert row.visible_value == "1220.00000000"
    assert row.digits_without_point == "122000000000"
    assert row.digit_count == 12
    assert row.code == 5
    assert isinstance(calculate_table2_value(1), Decimal)


def test_table2_example_5():
    row = format_table2_digits(5)
    assert row.visible_value == "244.000000000"
    assert row.digits_without_point == "244000000000"
    assert row.code == 10


def test_table2_example_3():
    row = format_table2_digits(3)
    assert row.visible_value == "406.666666667"
    assert row.digits_without_point == "406666666667"
    assert row.code == 65


def test_table2_all_100_have_12_digits_and_code_matches_sum():
    rows = generate_table2()
    assert len(rows) == 100
    seen = set()
    for row in rows:
        assert row.number not in seen
        seen.add(row.number)
        assert row.digit_count == TABLE2_DIGIT_COUNT
        assert len(row.digits_without_point) == 12
        assert row.code == sum(row.digit_list)
