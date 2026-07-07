from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install", "justech_multicurrency")
class TestJustechMulticurrencyRates(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.usd = cls.env.ref("base.USD")
        cls.usd.active = True

    def test_create_rate_with_origin(self):
        rate = self.env["res.currency.rate"].create(
            {
                "name": "2026-07-07",
                "currency_id": self.usd.id,
                "rate": 58.25,
                "justech_rate_origin": "manual",
            }
        )
        self.assertEqual(rate.justech_rate_origin, "manual")
        self.assertFalse(rate.justech_archived)

    def test_archive_and_restore_rate(self):
        rate = self.env["res.currency.rate"].create(
            {
                "name": "2026-07-06",
                "currency_id": self.usd.id,
                "rate": 58.0,
            }
        )
        rate.action_justech_archive_rate()
        self.assertTrue(rate.justech_archived)
        rate.action_justech_restore_rate()
        self.assertFalse(rate.justech_archived)

    def test_dashboard_shows_last_rate(self):
        self.env["res.currency.rate"].create(
            {
                "name": "2026-07-07",
                "currency_id": self.usd.id,
                "inverse_company_rate": 59.1,
                "justech_rate_origin": "import",
            }
        )
        policy = self.env["justech.multicurrency.policy"].get_policy(self.env.company)
        policy.commercial_currency_id = self.usd
        dash = self.env["justech.multicurrency.dashboard"].create({})
        if policy.commercial_currency_id != policy.accounting_currency_id:
            self.assertAlmostEqual(dash.last_rate_value, 59.1)
