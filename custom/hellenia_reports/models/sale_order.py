# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def get_hellenia_payment_term_display(self):
        """Etiqueta española para cotización: Contado o Crédito X días."""
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

    def get_hellenia_quotation_bottom_spacer_px(self):
        """Espacio flexible entre totales y condiciones (más con pocos ítems)."""
        self.ensure_one()
        lines = self._get_order_lines_to_report().filtered(
            lambda l: not l.display_type and not l.is_downpayment
        )
        count = len(lines)
        return max(0, min(440, 440 - count * 15))

    def get_hellenia_quotation_signature_spacer_px(self):
        """Espacio extra antes de firmas para anclarlas al cierre del documento."""
        self.ensure_one()
        lines = self._get_order_lines_to_report().filtered(
            lambda l: not l.display_type and not l.is_downpayment
        )
        count = len(lines)
        return max(0, min(100, 130 - count * 7))
