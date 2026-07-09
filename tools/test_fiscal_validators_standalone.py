#!/usr/bin/env python3
"""Pruebas de validadores puros sin instancia Odoo."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

VALIDATORS = Path(__file__).resolve().parents[1] / "custom" / "justech_l10n_do_base" / "validators"
sys.path.insert(0, str(VALIDATORS))

import fiscal_context  # noqa: E402
import ncf_format  # noqa: E402
import rnc_format  # noqa: E402


class TestRncFormat(unittest.TestCase):
    def test_normalize_vat(self):
        self.assertEqual(rnc_format.normalize_vat("1-31-00000-1"), "131000001")

    def test_valid_rnc_nine_digits(self):
        self.assertTrue(rnc_format.is_valid_rnc_format("131793916"))

    def test_valid_cedula_eleven_digits(self):
        self.assertTrue(rnc_format.is_valid_rnc_format("00112345678"))

    def test_invalid_short(self):
        self.assertFalse(rnc_format.is_valid_rnc_format("12345"))

    def test_dgii_id_type(self):
        self.assertEqual(rnc_format.dgii_id_type_from_vat("131793916"), "1")
        self.assertEqual(rnc_format.dgii_id_type_from_vat("00112345678"), "2")
        self.assertIsNone(rnc_format.dgii_id_type_from_vat("abc"))


class TestNcfFormat(unittest.TestCase):
    def test_validate_and_parse(self):
        ncf = ncf_format.validate_ncf_format("b0100000001")
        self.assertEqual(ncf, "B0100000001")
        prefix, seq = ncf_format.parse_ncf(ncf)
        self.assertEqual(prefix, "B01")
        self.assertEqual(seq, 1)

    def test_invalid_length(self):
        with self.assertRaises(ValueError):
            ncf_format.validate_ncf_format("B010001")

    def test_parse_invalid(self):
        self.assertEqual(ncf_format.parse_ncf("SHORT"), (False, False))


class TestFiscalContext(unittest.TestCase):
    def test_module_classification(self):
        self.assertEqual(fiscal_context.fiscal_module_for_move_type("out_invoice"), "ventas")
        self.assertEqual(fiscal_context.fiscal_module_for_move_type("in_invoice"), "compras")

    def test_duplicate_key_v2_sale(self):
        key = fiscal_context.fiscal_duplicate_key_v2(
            company_id=1,
            move_type="out_invoice",
            ncf="B0100000001",
            company_vat="131793916",
            partner_vat="999999999",
        )
        self.assertEqual(key, (1, "ventas", "B01", "B0100000001", "131793916"))

    def test_duplicate_key_v2_purchase(self):
        key = fiscal_context.fiscal_duplicate_key_v2(
            company_id=1,
            move_type="in_invoice",
            ncf="B1100000001",
            company_vat="131793916",
            partner_vat="401007336",
        )
        self.assertEqual(key, (1, "compras", "B11", "B1100000001", "401007336"))


if __name__ == "__main__":
    unittest.main()
