"""Tests Fase 21 — exportador DGII 607 y framework compartido."""
from datetime import date

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPhase21Dgii607(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.company
        if cls.company.country_id.code != "DO":
            cls.company.country_id = cls.env.ref("base.do")
        cls.company.justech_do_fiscal_enabled = True
        cls.tax_sale_18 = cls.env["account.tax"].search(
            [
                ("company_id", "=", cls.company.id),
                ("amount", "=", 18),
                ("type_tax_use", "=", "sale"),
            ],
            limit=1,
        )
        cls.tax_purchase_18 = cls.env["account.tax"].search(
            [
                ("company_id", "=", cls.company.id),
                ("amount", "=", 18),
                ("type_tax_use", "=", "purchase"),
            ],
            limit=1,
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Bien venta 607",
                "type": "consu",
                "is_storable": True,
                "list_price": 100.0,
                "taxes_id": [Command.set(cls.tax_sale_18.ids)],
            }
        )
        cls.journal_sale = cls.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.journal_purchase = cls.env["account.journal"].search(
            [("type", "=", "purchase"), ("company_id", "=", cls.company.id)],
            limit=1,
        )
        cls.doc_b02 = cls.env.ref("justech_l10n_do_base.doc_type_b02")
        cls.doc_b01 = cls.env.ref("justech_l10n_do_base.doc_type_b01")
        cls.doc_b04 = cls.env.ref("justech_l10n_do_base.doc_type_b04")
        cls.journal_sale.justech_do_use_ncf = True
        cls.journal_sale.justech_do_default_document_type_id = cls.doc_b02.id

    def _customer(self, name, vat=False, id_type=False):
        vals = {"name": name, "customer_rank": 1}
        if vat:
            vals["vat"] = vat
        if id_type:
            vals["justech_do_partner_id_type"] = id_type
        return self.env["res.partner"].create(vals)

    def _vendor(self, name, vat=False):
        return self.env["res.partner"].create(
            {"name": name, "supplier_rank": 1, "vat": vat or "131000099"}
        )

    def _sale_invoice(self, partner, ncf, doc_type=None, move_type="out_invoice", origin_ncf=False):
        vals = {
            "move_type": move_type,
            "partner_id": partner.id,
            "journal_id": self.journal_sale.id,
            "invoice_date": date.today(),
            "justech_do_ncf": ncf,
            "justech_do_document_type_id": (doc_type or self.doc_b02).id,
            "invoice_line_ids": [
                Command.create(
                    {
                        "product_id": self.product.id,
                        "quantity": 1,
                        "price_unit": 100.0,
                    }
                )
            ],
        }
        if origin_ncf:
            vals["justech_do_ncf_modified"] = origin_ncf
        move = self.env["account.move"].create(vals)
        move.action_post()
        return move

    def _purchase_invoice(self, partner, ncf):
        move = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": partner.id,
                "journal_id": self.journal_purchase.id,
                "invoice_date": date.today(),
                "justech_do_ncf": ncf,
                "justech_do_document_type_id": self.doc_b01.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "quantity": 1,
                            "price_unit": 50.0,
                            "tax_ids": [Command.set(self.tax_purchase_18.ids)],
                        }
                    )
                ],
            }
        )
        move.action_post()
        return move

    def test_validate_607_missing_ncf(self):
        partner = self._customer("Cliente sin NCF")
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": partner.id,
                "journal_id": self.journal_sale.id,
                "invoice_date": date.today(),
                "justech_do_document_type_id": self.doc_b02.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "quantity": 1,
                            "price_unit": 10.0,
                        }
                    )
                ],
            }
        )
        move.action_post()
        exporter = self.env["justech.do.dgii.607.exporter"]
        errors = exporter.validate_moves_607(
            self.company, date.today(), date.today()
        )
        self.assertTrue(any("NCF" in err for err in errors))

    def test_validate_607_invalid_ncf(self):
        partner = self._customer("Cliente NCF malo", "131000012", "1")
        move = self._sale_invoice(partner, "B0100000003", doc_type=self.doc_b01)
        move.write({"justech_do_ncf": "INVALID"})
        exporter = self.env["justech.do.dgii.607.exporter"]
        errors = exporter._dgii_validate_single_move(
            move, date.today(), date.today()
        )
        self.assertTrue(any("NCF inválido" in err for err in errors))

    def test_validate_607_missing_id_type(self):
        partner = self._customer("Cliente sin tipo", "131000013")
        self._sale_invoice(partner, "B0100000003", doc_type=self.doc_b01)
        exporter = self.env["justech.do.dgii.607.exporter"]
        errors = exporter.validate_moves_607(
            self.company, date.today(), date.today()
        )
        self.assertTrue(any("tipo de identificación" in err for err in errors))

    def test_validate_607_credit_note_requires_modified_ncf(self):
        partner = self._customer("Cliente NC", "131000014", "1")
        self._sale_invoice(
            partner,
            "B0400000001",
            doc_type=self.doc_b04,
            move_type="out_refund",
        )
        exporter = self.env["justech.do.dgii.607.exporter"]
        errors = exporter.validate_moves_607(
            self.company, date.today(), date.today()
        )
        self.assertTrue(any("NCF modificado" in err for err in errors))

    def test_validate_607_consumer_without_vat(self):
        partner = self._customer("Consumidor final")
        self._sale_invoice(partner, "B0200000001", doc_type=self.doc_b02)
        exporter = self.env["justech.do.dgii.607.exporter"]
        result = exporter.validate_period_607(
            self.company, date.today(), date.today()
        )
        self.assertGreaterEqual(result["counts"]["valid"], 1)

    def test_607_excludes_purchase_documents(self):
        vendor = self._vendor("Proveedor compra")
        self._purchase_invoice(vendor, "B0100000099")
        partner = self._customer("Cliente venta", "131000015", "1")
        self._sale_invoice(partner, "B0100000004", doc_type=self.doc_b01)
        exporter = self.env["justech.do.dgii.607.exporter"]
        result = exporter.validate_period_607(
            self.company, date.today(), date.today()
        )
        move_types = result["buckets"]["all"].mapped("move_type")
        self.assertNotIn("in_invoice", move_types)
        self.assertIn("out_invoice", move_types)

    def test_export_607_xlsx(self):
        partner = self._customer("Cliente 607", "131000010", "1")
        self._sale_invoice(partner, "B0100000001", doc_type=self.doc_b01)
        exporter = self.env["justech.do.dgii.607.exporter"]
        content, filename = exporter.export_xlsx(
            self.company, date.today(), date.today()
        )
        self.assertTrue(content)
        self.assertIn("607", filename)

    def test_607_sales_summary(self):
        partner = self._customer("Cliente resumen", "131000016", "1")
        self._sale_invoice(partner, "B0100000005", doc_type=self.doc_b01)
        exporter = self.env["justech.do.dgii.607.exporter"]
        result = exporter.validate_period_607(
            self.company, date.today(), date.today()
        )
        summary = exporter.format_validation_summary(result)
        self.assertIn("Facturas exportables", summary)
        self.assertIn("ITBIS facturado", summary)
        self.assertIn("Ventas gravadas", summary)

    def test_review_workflow_607(self):
        partner = self._customer("Cliente workflow", "131000011", "1")
        self._sale_invoice(partner, "B0100000002", doc_type=self.doc_b01)
        report = self.env["justech.do.fiscal.report"].create(
            {
                "name": "607 Test Review",
                "report_type": "607",
                "period_code": date.today().strftime("%Y%m"),
                "date_from": date.today().replace(day=1),
                "date_to": date.today(),
                "company_id": self.company.id,
            }
        )
        report.action_load_review_lines()
        report.action_validate_period()
        self.assertEqual(report.state, "validated")
        self.assertGreater(report.review_valid_count, 0)
        self.assertEqual(report.count_valid, report.review_valid_count)
        self.assertIn("607", report.validation_log or "")
        self.assertIn("Facturas exportables", report.validation_log or "")

    def test_counters_sync_after_validate(self):
        partner = self._customer("Cliente sync", "131000017", "1")
        self._sale_invoice(partner, "B0100000006", doc_type=self.doc_b01)
        report = self.env["justech.do.fiscal.report"].create(
            {
                "name": "607 Sync Counters",
                "report_type": "607",
                "period_code": date.today().strftime("%Y%m"),
                "date_from": date.today().replace(day=1),
                "date_to": date.today(),
                "company_id": self.company.id,
            }
        )
        report.action_load_review_lines()
        report.action_validate_period()
        self.assertEqual(report.count_all, report.review_line_count)
        self.assertEqual(report.count_valid, report.review_valid_count)
        valid_lines = report.line_ids.filtered(
            lambda l: l.include_in_report and l.fiscal_state == "valid"
        )
        self.assertEqual(report.count_valid, len(valid_lines))

    def test_shared_exporter_dispatch(self):
        report606 = self.env["justech.do.fiscal.report"].new({"report_type": "606"})
        report607 = self.env["justech.do.fiscal.report"].new({"report_type": "607"})
        self.assertEqual(
            report606._get_dgii_exporter()._name, "justech.do.dgii.606.exporter"
        )
        self.assertEqual(
            report607._get_dgii_exporter()._name, "justech.do.dgii.607.exporter"
        )
