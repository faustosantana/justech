from odoo.tests import tagged

from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestJustechL10nDoBase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

    def test_document_types_loaded(self):
        prefixes = {"B01", "B02", "B03", "B04", "B11", "B13"}
        types = self.env["justech.do.fiscal.document.type"].search([])
        found = set(types.mapped("prefix"))
        self.assertTrue(prefixes.issubset(found))

    def test_ncf_format(self):
        doc = self.env.ref("justech_l10n_do_base.doc_type_b02")
        ncf = doc.format_ncf(123)
        self.assertEqual(ncf, "B0200000123")
        self.assertEqual(len(ncf), 11)

    def test_rnc_validation(self):
        partner = self.env["res.partner"].create(
            {"name": "Test RNC", "vat": "131-793-916"}
        )
        self.assertTrue(partner.justech_do_rnc_valid)
