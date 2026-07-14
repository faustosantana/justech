# -*- coding: utf-8 -*-
"""UX Compras — etiquetas y Cotización de referencia (sin lógica fiscal)."""
from odoo import _, api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    justech_reference_sale_order_id = fields.Many2one(
        "sale.order",
        string="Cotización de referencia",
        compute="_compute_justech_reference_sale_order_id",
        readonly=True,
        help="Cotización/Pedido de venta origen vía sale_line_id (relación real). "
        "Vacío si la OC fue creada manualmente. No reutiliza partner_ref.",
    )

    @api.depends("order_line.sale_line_id", "order_line.sale_order_id")
    def _compute_justech_reference_sale_order_id(self):
        for order in self:
            if hasattr(order, "_get_sale_orders"):
                sales = order._get_sale_orders()
            else:
                sales = order.order_line.mapped("sale_order_id")
            # Un solo origen → enlace directo; múltiples → vacío (smart button Sale).
            order.justech_reference_sale_order_id = sales[:1] if len(sales) == 1 else False

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """Solo etiquetas UX: no cambia claves técnicas de estado."""
        res = super().fields_get(allfields=allfields, attributes=attributes)
        if "state" in res and res["state"].get("selection"):
            label_map = {
                "draft": _("Solicitud de Orden"),
                "sent": _("Solicitud de Orden enviada"),
            }
            res["state"]["selection"] = [
                (key, label_map.get(key, label))
                for key, label in res["state"]["selection"]
            ]
        if "partner_ref" in res:
            res["partner_ref"]["string"] = _("Referencia del proveedor")
        return res
