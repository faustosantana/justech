from odoo import fields
from odoo import fields
from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseCommon


def _ensure_usd_rate(env, value, rate_date=None, company=None):
    """Asegura tasa USD en convención Odoo 19 (inverse_company_rate = DOP por 1 USD)."""
    rate_date = rate_date or fields.Date.today()
    usd = env.ref("base.USD")
    usd.active = True
    company = company or env.company
    Rate = env["res.currency.rate"]
    existing = Rate.search(
        [
            ("currency_id", "=", usd.id),
            ("name", "=", rate_date),
            ("company_id", "in", [company.id, False]),
        ],
        limit=1,
    )
    vals = {
        "inverse_company_rate": value,
        "company_id": company.id,
    }
    if existing:
        existing.write(vals)
        return existing
    return Rate.create(
        {
            "name": rate_date,
            "currency_id": usd.id,
            **vals,
        }
    )


@tagged("post_install", "-at_install", "justech_multicurrency")
class TestJustechCommercialPricing(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.usd = cls.env.ref("base.USD")
        cls.usd.active = True
        cls.dop = cls.env.ref("base.DOP")
        cls.dop.active = True
        cls.company = cls.env["res.company"].create(
            {
                "name": "Justech MC Test DOP",
                "currency_id": cls.dop.id,
            }
        )
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=cls.company.ids))
        cls.policy = cls.env["justech.multicurrency.policy"].with_company(cls.company).get_policy(
            cls.company
        )
        cls.usd_pl = cls.env["justech.multicurrency.policy"]._find_or_create_public_pricelist(
            cls.company, cls.usd
        )

    def setUp(self):
        super().setUp()
        _ensure_usd_rate(self.env, 58.0, company=self.company)
        self.env.flush_all()

    def test_fx_conversion_available_in_tests(self):
        rate = self.env["res.currency.rate"].sudo().search(
            [
                ("currency_id", "=", self.usd.id),
                ("name", "=", fields.Date.today()),
                ("company_id", "in", [self.env.company.id, False]),
            ],
            limit=1,
        )
        self.assertTrue(rate, "Tasa USD no encontrada en el entorno de prueba")
        self.assertAlmostEqual(rate.inverse_company_rate, 58.0, places=2)
        converted = self.env["justech.multicurrency.policy"].convert_to_company_currency(
            10.0, self.usd
        )
        self.assertAlmostEqual(converted, 580.0, places=2)

    def test_usd_sale_syncs_list_price_and_pricelist(self):
        template = self.env["product.template"].with_company(self.company).create(
            {
                "name": "Commercial USD Product",
                "justech_sale_price": 10.0,
                "justech_sale_currency_id": self.usd.id,
            }
        )
        self.assertAlmostEqual(template.list_price, 580.0, places=2)
        item = self.env["product.pricelist.item"].search(
            [
                ("pricelist_id", "=", self.usd_pl.id),
                ("product_tmpl_id", "=", template.id),
            ],
            limit=1,
        )
        self.assertTrue(item)
        self.assertEqual(item.compute_price, "fixed")
        self.assertAlmostEqual(item.fixed_price, 10.0, places=2)

    def test_dop_sale_keeps_list_price(self):
        template = self.env["product.template"].with_company(self.company).create(
            {
                "name": "Commercial DOP Product",
                "justech_sale_price": 1500.0,
                "justech_sale_currency_id": self.dop.id,
            }
        )
        self.assertAlmostEqual(template.list_price, 1500.0, places=2)

    def test_usd_purchase_syncs_standard_price(self):
        template = self.env["product.template"].with_company(self.company).create(
            {
                "name": "Commercial USD Cost",
                "justech_purchase_price": 5.0,
                "justech_purchase_currency_id": self.usd.id,
            }
        )
        self.assertAlmostEqual(template.standard_price, 290.0, places=2)

    def test_rate_change_resyncs_list_price(self):
        template = self.env["product.template"].with_company(self.company).create(
            {
                "name": "Commercial USD Resync",
                "justech_sale_price": 20.0,
                "justech_sale_currency_id": self.usd.id,
            }
        )
        self.assertAlmostEqual(template.list_price, 1160.0, places=2)
        _ensure_usd_rate(self.env, 60.0, rate_date=fields.Date.today())
        template.invalidate_recordset()
        self.assertAlmostEqual(template.list_price, 1200.0, places=2)

    def test_seller_fields_without_manual_pricelist(self):
        template = self.env["product.template"].with_company(self.company).create(
            {
                "name": "No manual pricelist",
                "company_id": self.company.id,
                "justech_sale_price": 25.0,
                "justech_sale_currency_id": self.usd.id,
            }
        )
        self.assertAlmostEqual(template.list_price, 1450.0, places=2)
        item = self.env["product.pricelist.item"].sudo().search(
            [("product_tmpl_id", "=", template.id)],
            limit=1,
        )
        self.assertTrue(item)
        self.assertEqual(item.pricelist_id.currency_id, self.usd)
