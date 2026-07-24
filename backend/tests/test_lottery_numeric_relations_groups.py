"""Fase A — agrupaciones y catálogo separados T1/T2."""

from __future__ import annotations

from app.lottery.numeric_relations.catalog import build_catalog
from app.lottery.numeric_relations.table1 import format_table1_digits


def test_catalog_maps_bidirectional_and_separated():
    cat = build_catalog(force_rebuild=True)
    assert len(cat.table1_number_to_code) == 100
    assert len(cat.table2_number_to_code) == 100

    for n, code in cat.table1_number_to_code.items():
        assert n in cat.table1_code_to_numbers[code]
        assert format_table1_digits(n).code == code

    for n, code in cat.table2_number_to_code.items():
        assert n in cat.table2_code_to_numbers[code]

    # Separation: same number can have different codes across tables
    assert cat.table1_number_to_code[1] == 34
    assert cat.table2_number_to_code[1] == 5

    # Groups sorted unique
    for nums in cat.table1_code_to_numbers.values():
        assert nums == sorted(set(nums))
    for nums in cat.table2_code_to_numbers.values():
        assert nums == sorted(set(nums))


def test_get_companions_for_mother_code_34_includes_1():
    cat = build_catalog()
    companions = cat.get_table1_companions(34)
    assert 1 in companions
    assert companions == sorted(companions)


def test_exclude_self_neighbors():
    cat = build_catalog()
    # Pick any number; neighbors must not include self
    for n in (1, 5, 34, 100):
        neigh = cat.get_table2_neighbors(n, exclude_self=True)
        assert n not in neigh
        full = cat.get_table2_neighbors(n, exclude_self=False)
        assert n in full
