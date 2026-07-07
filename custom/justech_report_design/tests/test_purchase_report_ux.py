from odoo.tests import tagged

from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPurchaseReportUx(TransactionCase):
    def test_band_title_by_state(self):
        PO = self.env["purchase.order"]
        partner = self.env["res.partner"].create({"name": "Proveedor UX Test"})
        product = self.env["product.product"].create(
            {"name": "Producto UX Test", "type": "consu", "purchase_ok": True}
        )
        po = PO.create(
            {
                "partner_id": partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "name": product.display_name,
                            "product_id": product.id,
                            "product_qty": 1,
                            "price_unit": 100,
                        },
                    )
                ],
            }
        )
        expectations = [
            ("draft", "SOLICITUD DE COTIZACIÓN"),
            ("sent", "SOLICITUD DE COTIZACIÓN"),
            ("purchase", "ORDEN DE COMPRA"),
        ]
        for state, expected in expectations:
            po.write({"state": state})
            self.assertEqual(po.get_jt_po_band_title(), expected)

    def test_official_report_template(self):
        report_po = self.env.ref("purchase.action_report_purchase_order")
        report_rfq = self.env.ref("purchase.report_purchase_quotation")
        self.assertIn(
            "justech_report_design.report_justech_purchase_order_document",
            report_po.report_name,
        )
        self.assertIn(
            "justech_report_design.report_justech_purchase_order_document",
            report_rfq.report_name,
        )

    def test_template_uses_corporate_band(self):
        view = self.env.ref(
            "justech_report_design.justech_purchase_order_body", raise_if_not_found=False
        )
        self.assertTrue(view)
        arch = view.arch_db or ""
        self.assertIn("jt-hq-band", arch)
        self.assertIn("get_jt_po_band_title", arch)
        self.assertNotIn("Purchase Order", arch)
        self.assertNotIn("jt-po-band-title-cell", arch)
