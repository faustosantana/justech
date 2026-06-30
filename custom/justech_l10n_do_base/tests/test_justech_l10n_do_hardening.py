from odoo.tests import tagged

from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestJustechL10nDoBaseHardening(TransactionCase):
    def test_fiscal_document_type_record_rule(self):
        rules = self.env["ir.rule"].search(
            [("model_id.model", "=", "justech.do.fiscal.document.type")]
        )
        self.assertTrue(
            rules.filtered(lambda r: "company_ids" in (r.domain_force or ""))
        )
