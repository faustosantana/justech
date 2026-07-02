# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def get_jt_payment_term_display(self):
        """Etiqueta española: Contado o Crédito a X días."""
        self.ensure_one()
        term = self.payment_term_id
        if not term:
            return "Contado"
        days = [int(d) for d in term.line_ids.mapped("nb_days") if d is not None]
        max_days = max(days) if days else 0
        name = (term.name or "").strip().lower()
        if max_days <= 0 or "immediate" in name or "contado" in name or "cash" in name:
            return "Contado"
        return f"Crédito a {max_days} días"

    def get_jt_quotation_bottom_spacer_px(self):
        """Espaciador mínimo post-totales (sin hueco grande en página)."""
        self.ensure_one()
        lines = self._get_order_lines_to_report().filtered(
            lambda l: not l.display_type and not l.is_downpayment
        )
        count = len(lines)
        if count <= 5:
            return 0
        if count <= 15:
            return 8
        return 4

    def get_jt_quotation_signature_spacer_px(self):
        return 0
