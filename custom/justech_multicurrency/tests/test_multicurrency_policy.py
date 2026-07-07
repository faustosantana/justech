from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install", "justech_multicurrency")
class TestJustechMulticurrencyPolicy(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Policy = cls.env["justech.multicurrency.policy"]
        cls.usd = cls.env.ref("base.USD")
        cls.usd.active = True
        cls.dop = cls.env.ref("base.DOP") if cls.env.ref("base.DOP", raise_if_not_found=False) else cls.env.company.currency_id
        cls.policy = cls.Policy.get_policy(cls.env.company)

    def test_company_dop_policy_exists(self):
        self.assertTrue(self.policy)
        self.assertEqual(self.policy.accounting_currency_id, self.env.company.currency_id)

    def test_company_usd_commercial_sync(self):
        policy = self.policy
        policy.write({"commercial_currency_id": self.usd.id})
        policy._sync_commercial_currency_defaults()
        self.assertEqual(policy.default_pricelist_id.currency_id, self.usd)
        self.assertEqual(policy.default_product_pricelist_id.currency_id, self.usd)
        self.assertEqual(policy.default_customer_currency_id, self.usd)

    def test_pricelist_currency_constraint(self):
        dop = self.env["res.currency"].with_context(active_test=False).search(
            [("name", "=", "DOP")], limit=1
        )
        if not dop:
            self.skipTest("Moneda DOP no disponible en el entorno de prueba")
        dop_pl = self.env["product.pricelist"].create(
            {
                "name": "Test DOP list MC2 constraint",
                "currency_id": dop.id,
                "company_id": self.env.company.id,
            }
        )
        self.policy.write({"commercial_currency_id": self.usd.id})
        with self.assertRaises(ValidationError):
            self.policy.write({"default_pricelist_id": dop_pl.id})

    def test_public_pricelist_list(self):
        pl = self.Policy._find_or_create_public_pricelist(self.env.company, self.usd)
        self.assertEqual(pl.currency_id, self.usd)
        pl2 = self.Policy._find_or_create_public_pricelist(self.env.company, self.usd)
        self.assertEqual(pl.id, pl2.id)

    def test_dashboard_readonly_snapshot(self):
        dash = self.env["justech.multicurrency.dashboard"].create({"policy_id": self.policy.id})
        self.assertEqual(dash.accounting_currency_id, self.env.company.currency_id)
        self.assertTrue(dash.summary_html)
