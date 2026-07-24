"""Fase A — Tabla 1: ejemplos documentales + 1..100."""

from __future__ import annotations

from decimal import Decimal

from app.lottery.numeric_relations.constants import TABLE1_DIGIT_COUNT
from app.lottery.numeric_relations.table1 import (
    calculate_table1_value,
    format_table1_digits,
    generate_table1,
)


def test_table1_example_1():
    row = format_table1_digits(1)
    assert row.visible_value == "0.0008196721"
    assert row.digits_without_point == "00008196721"
    assert row.digit_count == 11
    assert row.code == 34
    assert isinstance(calculate_table1_value(1), Decimal)


def test_table1_example_5():
    row = format_table1_digits(5)
    assert row.visible_value == "0.0040983607"
    assert len(row.digits_without_point) == 11
    assert row.code == 37


def test_table1_all_100_have_11_digits_and_code_matches_sum():
    rows = generate_table1()
    assert len(rows) == 100
    seen = set()
    for row in rows:
        assert row.number not in seen
        seen.add(row.number)
        assert row.digit_count == TABLE1_DIGIT_COUNT
        assert len(row.digits_without_point) == 11
        assert row.code == sum(row.digit_list)
        assert "." not in row.digits_without_point
