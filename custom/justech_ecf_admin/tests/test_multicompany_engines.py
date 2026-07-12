from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestMultiCompanyEngines(TransactionCase):
    def test_production_gate_and_modes(self):
        companies = self.env["res.company"].search([], limit=4)
        self.assertGreaterEqual(len(companies), 1)
        Config = self.env["justech.ecf.company.config"]
        justech = companies.filtered(lambda c: "JUSTECH" in (c.name or "").upper())[:1] or companies[0]
        others = companies - justech
        cfg = Config.search([("company_id", "=", justech.id)], limit=1)
        if not cfg:
            cfg = Config.create({"company_id": justech.id})
        cfg.write({"fiscal_mode": "ecf_certification", "dgii_environment": "mock"})
        for co in others[:3]:
            c = Config.search([("company_id", "=", co.id)], limit=1)
            if not c:
                c = Config.create({"company_id": co.id, "fiscal_mode": "traditional_ncf", "dgii_environment": "mock"})
            else:
                c.write({"fiscal_mode": "traditional_ncf", "dgii_environment": "mock"})
        with self.assertRaises(ValidationError):
            cfg.write({"dgii_environment": "ecf", "fiscal_mode": "ecf_production", "production_gate_unlocked": False})
