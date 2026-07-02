from datetime import date, timedelta

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestJustechL10nDoNcf(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.company = cls.env.company
        if cls.company.country_id.code != "DO":
            cls.company.country_id = cls.env.ref("base.do")
        cls.company.justech_do_fiscal_enabled = True
        cls.tax_18 = cls.env["account.tax"].search(
            [
                ("company_id", "=", cls.company.id),
                ("amount", "=", 18),
                ("type_tax_use", "=", "sale"),
            ],
            limit=1,
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Product NCF",
                "type": "consu",
                "is_storable": True,
                "list_price": 100.0,
                "taxes_id": [Command.set(cls.tax_18.ids)],
            }
        )
        cls.journal_sale = cls.env["account.journal"].search(
            [("type", "=", "sale"), ("company_id", "=", cls.company.id)], limit=1
        )
        cls.journal_sale.write(
            {
                "justech_do_use_ncf": True,
                "justech_do_document_type_ids": [
                    Command.set(
                        cls.env["justech.do.fiscal.document.type"].search([]).ids
                    )
                ],
            }
        )
        cls.journal_purchase = cls.env["account.journal"].search(
            [("type", "=", "purchase"), ("company_id", "=", cls.company.id)], limit=1
        )
        cls.doc_b01 = cls.env.ref("justech_l10n_do_base.doc_type_b01")
        cls.doc_b02 = cls.env.ref("justech_l10n_do_base.doc_type_b02")
        cls.doc_b04 = cls.env.ref("justech_l10n_do_base.doc_type_b04")
        cls.doc_b11 = cls.env.ref("justech_l10n_do_base.doc_type_b11")
        cls.doc_b13 = cls.env.ref("justech_l10n_do_base.doc_type_b13")
        manager = cls.env.ref("justech_l10n_do_base.group_justech_do_fiscal_manager")
        cls.env.user.write({"group_ids": [(4, manager.id)]})

    def _create_range(self, doc, start=1, end=100, **kwargs):
        today = date.today()
        return self.env["justech.do.ncf.range"].create(
            {
                "name": f"Range {doc.prefix}",
                "document_type_id": doc.id,
                "company_id": self.company.id,
                "sequence_start": start,
                "sequence_end": end,
                "next_sequence": start,
                "date_from": today - timedelta(days=30),
                "date_to": today + timedelta(days=365),
                "journal_ids": [Command.set(self.journal_sale.ids)],
                **kwargs,
            }
        )

    def _invoice_vals(self, partner, move_type="out_invoice", journal=None):
        journal = journal or self.journal_sale
        return {
            "move_type": move_type,
            "partner_id": partner.id,
            "journal_id": journal.id,
            "invoice_date": date.today(),
            "invoice_line_ids": [
                Command.create(
                    {
                        "product_id": self.product.id,
                        "quantity": 1,
                        "price_unit": 100.0,
                        "tax_ids": [Command.set(self.tax_18.ids)],
                    }
                )
            ],
        }

    def test_b02_consumer_invoice(self):
        self._create_range(self.doc_b02).action_activate()
        partner = self.env["res.partner"].create({"name": "Consumidor Final"})
        move = self.env["account.move"].create(self._invoice_vals(partner))
        move.action_post()
        self.assertTrue(move.justech_do_ncf.startswith("B02"))
        self.assertEqual(move.state, "posted")

    def test_b01_requires_rnc(self):
        self._create_range(self.doc_b01).action_activate()
        partner = self.env["res.partner"].create({"name": "Cliente B2B", "vat": "131793916"})
        move = self.env["account.move"].create(self._invoice_vals(partner))
        move.action_post()
        self.assertTrue(move.justech_do_ncf.startswith("B01"))

    def test_credit_note_b04(self):
        self._create_range(self.doc_b02).action_activate()
        self._create_range(self.doc_b04).action_activate()
        partner = self.env["res.partner"].create({"name": "CF"})
        inv = self.env["account.move"].create(self._invoice_vals(partner))
        inv.action_post()
        cn = inv._reverse_moves(
            default_values_list=[{"invoice_date": date.today()}]
        )
        cn.action_post()
        self.assertTrue(cn.justech_do_ncf.startswith("B04"))

    def test_duplicate_ncf_blocked(self):
        self._create_range(self.doc_b02).action_activate()
        partner = self.env["res.partner"].create({"name": "CF"})
        m1 = self.env["account.move"].create(self._invoice_vals(partner))
        m1.action_post()
        ncf = m1.justech_do_ncf
        m2 = self.env["account.move"].create(self._invoice_vals(partner))
        m2.justech_do_ncf = ncf
        with self.assertRaises(ValidationError):
            m2.action_post()

    def test_depleted_range_blocked(self):
        journal = self.env["account.journal"].create(
            {
                "name": "Depleted Test Journal",
                "code": "XPD",
                "type": "sale",
                "company_id": self.company.id,
                "justech_do_use_ncf": True,
                "justech_do_document_type_ids": [Command.set([self.doc_b02.id])],
            }
        )
        ncf_range = self.env["justech.do.ncf.range"].create(
            {
                "name": "Range B02 Depleted",
                "document_type_id": self.doc_b02.id,
                "company_id": self.company.id,
                "sequence_start": 1,
                "sequence_end": 1,
                "next_sequence": 1,
                "date_from": date.today() - timedelta(days=1),
                "date_to": date.today() + timedelta(days=30),
                "journal_ids": [Command.set(journal.ids)],
            }
        )
        ncf_range.action_activate()
        partner = self.env["res.partner"].create({"name": "CF"})
        move = self.env["account.move"].create(
            self._invoice_vals(partner, journal=journal)
        )
        move.action_post()
        self.assertEqual(ncf_range.state, "depleted")
        move2 = self.env["account.move"].create(
            self._invoice_vals(partner, journal=journal)
        )
        with self.assertRaises(Exception):
            move2.action_post()

    def test_expired_range_blocked(self):
        journal = self.env["account.journal"].create(
            {
                "name": "Expired Test Journal",
                "code": "XPE",
                "type": "sale",
                "company_id": self.company.id,
                "justech_do_use_ncf": True,
                "justech_do_document_type_ids": [Command.set([self.doc_b02.id])],
            }
        )
        ncf_range = self.env["justech.do.ncf.range"].create(
            {
                "name": "Range B02 Expired",
                "document_type_id": self.doc_b02.id,
                "company_id": self.company.id,
                "sequence_start": 1,
                "sequence_end": 100,
                "next_sequence": 1,
                "date_from": date.today() - timedelta(days=30),
                "date_to": date.today() + timedelta(days=30),
                "journal_ids": [Command.set(journal.ids)],
            }
        )
        ncf_range.action_activate()
        ncf_range.write(
            {
                "date_from": date.today() - timedelta(days=60),
                "date_to": date.today() - timedelta(days=1),
            }
        )
        partner = self.env["res.partner"].create({"name": "CF"})
        move = self.env["account.move"].create(
            self._invoice_vals(partner, journal=journal)
        )
        with self.assertRaises(Exception):
            move.action_post()

    def test_b11_purchase(self):
        journal = self.journal_purchase
        journal.write(
            {
                "justech_do_use_ncf": True,
                "justech_do_default_document_type_id": self.doc_b11.id,
                "justech_do_document_type_ids": [Command.set([self.doc_b11.id])],
            }
        )
        self.env["justech.do.ncf.range"].create(
            {
                "name": "B11 Range",
                "document_type_id": self.doc_b11.id,
                "company_id": self.company.id,
                "sequence_start": 1,
                "sequence_end": 50,
                "next_sequence": 1,
                "date_from": date.today() - timedelta(days=1),
                "date_to": date.today() + timedelta(days=365),
                "journal_ids": [Command.set(journal.ids)],
            }
        ).action_activate()
        vendor = self.env["res.partner"].create({"name": "Informal Vendor"})
        move = self.env["account.move"].create(
            self._invoice_vals(vendor, move_type="in_invoice", journal=journal)
        )
        move.action_post()
        self.assertTrue(move.justech_do_ncf.startswith("B11"))

    def test_void_ncf(self):
        self._create_range(self.doc_b02).action_activate()
        partner = self.env["res.partner"].create({"name": "CF"})
        move = self.env["account.move"].create(self._invoice_vals(partner))
        move.action_post()
        move.justech_do_ncf_void_reason = "Test void fiscal"
        move.action_void_ncf()
        self.assertTrue(move.justech_do_ncf_voided)
        consumption = self.env["justech.do.ncf.consumption"].search(
            [("move_id", "=", move.id)], limit=1
        )
        self.assertEqual(consumption.state, "voided")
        self.assertEqual(consumption.void_user_id, self.env.user)
        self.assertTrue(consumption.void_reason)

    def test_void_ncf_requires_manager(self):
        self._create_range(self.doc_b02).action_activate()
        partner = self.env["res.partner"].create({"name": "CF"})
        move = self.env["account.move"].create(self._invoice_vals(partner))
        move.action_post()
        move.justech_do_ncf_void_reason = "Should fail"
        fiscal_user = self.env["res.users"].create(
            {
                "name": "Fiscal User Only",
                "login": f"fiscal_user_{self.env.cr.dbname}@test.com",
                "group_ids": [
                    Command.set(
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref(
                                "justech_l10n_do_base.group_justech_do_fiscal_user"
                            ).id,
                        ]
                    )
                ],
            }
        )
        with self.assertRaises(AccessError):
            move.with_user(fiscal_user).action_void_ncf()

    def test_void_ncf_requires_reason(self):
        self._create_range(self.doc_b02).action_activate()
        partner = self.env["res.partner"].create({"name": "CF"})
        move = self.env["account.move"].create(self._invoice_vals(partner))
        move.action_post()
        with self.assertRaises(UserError):
            move.action_void_ncf()

    def test_record_rules_exist(self):
        models = [
            "justech.do.ncf.range",
            "justech.do.ncf.consumption",
        ]
        for model_name in models:
            rules = self.env["ir.rule"].search(
                [("model_id.model", "=", model_name)]
            )
            self.assertTrue(
                rules.filtered(lambda r: "company" in (r.domain_force or "")),
                f"Missing company rule for {model_name}",
            )

    def test_consume_next_sequential_unique(self):
        journal = self.env["account.journal"].create(
            {
                "name": "Lock Test Journal",
                "code": "XLK",
                "type": "sale",
                "company_id": self.company.id,
                "justech_do_use_ncf": True,
                "justech_do_document_type_ids": [Command.set([self.doc_b02.id])],
            }
        )
        ncf_range = self.env["justech.do.ncf.range"].create(
            {
                "name": "Lock Range",
                "document_type_id": self.doc_b02.id,
                "company_id": self.company.id,
                "sequence_start": 8000,
                "sequence_end": 8010,
                "next_sequence": 8000,
                "date_from": date.today() - timedelta(days=1),
                "date_to": date.today() + timedelta(days=30),
                "journal_ids": [Command.set(journal.ids)],
            }
        )
        ncf_range.action_activate()
        partner = self.env["res.partner"].create({"name": "Lock CF"})
        move1 = self.env["account.move"].create(
            self._invoice_vals(partner, journal=journal)
        )
        move2 = self.env["account.move"].create(
            self._invoice_vals(
                self.env["res.partner"].create({"name": "Lock CF 2"}),
                journal=journal,
            )
        )
        move1.action_post()
        move2.action_post()
        self.assertNotEqual(move1.justech_do_ncf, move2.justech_do_ncf)
        ncf_range.invalidate_recordset()
        self.assertEqual(ncf_range.next_sequence, 8002)
