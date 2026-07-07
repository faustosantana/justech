from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install", "justech_multicurrency")
class TestJustechMulticurrencyAutomation(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.usd = cls.env.ref("base.USD")
        cls.usd.active = True
        cls.policy = cls.env["justech.multicurrency.policy"].get_policy(cls.env.company)
        cls.usd_pl = cls.env["justech.multicurrency.policy"]._find_or_create_public_pricelist(
            cls.env.company, cls.usd
        )
        cls.policy.write(
            {
                "commercial_currency_id": cls.usd.id,
                "default_pricelist_id": cls.usd_pl.id,
                "default_product_pricelist_id": cls.usd_pl.id,
                "default_customer_currency_id": cls.usd.id,
                "default_supplier_currency_id": cls.usd.id,
            }
        )

    def setUp(self):
        super().setUp()
        from odoo.addons.justech_multicurrency.tests.test_commercial_pricing import _ensure_usd_rate

        _ensure_usd_rate(self.env, 58.0)

    def test_new_customer_inherits_usd_pricelist(self):
        partner = self.env["res.partner"].create(
            {
                "name": "MC2 Customer USD",
                "customer_rank": 1,
            }
        )
        pl = partner.with_company(self.env.company).property_product_pricelist
        self.assertEqual(pl, self.usd_pl)

    def test_new_supplier_inherits_usd_currency(self):
        partner = self.env["res.partner"].create(
            {
                "name": "MC2 Supplier USD",
                "supplier_rank": 1,
            }
        )
        if "property_purchase_currency_id" in partner._fields:
            currency = partner.with_company(self.env.company).property_purchase_currency_id
            self.assertEqual(currency, self.usd)

    def test_new_product_usd_commercial_price(self):
        dop = self.env.ref("base.DOP")
        dop.active = True
        company = self.env["res.company"].create(
            {"name": "MC2 Automation DOP", "currency_id": dop.id}
        )
        usd_pl = self.env["justech.multicurrency.policy"]._find_or_create_public_pricelist(
            company, self.usd
        )
        from odoo.addons.justech_multicurrency.tests.test_commercial_pricing import _ensure_usd_rate

        _ensure_usd_rate(self.env, 58.0, company=company)
        template = self.env["product.template"].with_company(company).create(
            {
                "name": "MC2 Product USD Commercial",
                "justech_sale_price": 100.0,
                "justech_sale_currency_id": self.usd.id,
            }
        )
        item = self.env["product.pricelist.item"].search(
            [
                ("pricelist_id", "=", usd_pl.id),
                ("product_tmpl_id", "=", template.id),
            ]
        )
        self.assertTrue(item)
        self.assertEqual(item.compute_price, "fixed")
        self.assertAlmostEqual(item.fixed_price, 100.0, places=2)
        self.assertAlmostEqual(template.list_price, 5800.0, places=2)
