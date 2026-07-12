from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestDgiiMock(TransactionCase):
    def test_service_catalog_official(self):
        cat = self.env["justech.ecf.dgii.client"].service_catalog()
        self.assertIn("testecf", cat["environments"])
        self.assertIn("ecf", cat["environments"])
        self.assertTrue(cat["services"])

    def test_production_blocked(self):
        co = self.env.company
        cfg = self.env["justech.ecf.company.config"].search([("company_id", "=", co.id)], limit=1)
        if not cfg:
            cfg = self.env["justech.ecf.company.config"].create({"company_id": co.id})
        # cannot set ecf without gate
        with self.assertRaises(Exception):
            cfg.write({"dgii_environment": "ecf", "fiscal_mode": "ecf_production"})
