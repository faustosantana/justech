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

    def format_jt_discount_percent(self, discount):
        """Porcentaje de descuento para columna DESC. en cotización."""
        value = discount or 0
        if value == int(value):
            return f"{int(value)}%"
        return f"{value:g}%"

    def get_jt_quotation_has_discount(self):
        """True si alguna línea reportable tiene descuento > 0."""
        self.ensure_one()
        lines = self._get_order_lines_to_report().filtered(
            lambda l: not l.display_type and not l.is_downpayment
        )
        return any((l.discount or 0) > 0 for l in lines)

    def get_jt_quotation_signature_spacer_px(self):
        """Spacer flexible condiciones → firmas; empuja firmas hacia el footer."""
        self.ensure_one()
        lines = self._get_order_lines_to_report().filtered(
            lambda l: not l.display_type and not l.is_downpayment
        )
        count = len(lines)
        lines_per_page = 22
        if count > lines_per_page:
            return 28
        page_usable = 900
        fixed = 420
        line_h = 34
        sig_h = 85
        footer_gap = 55
        used = fixed + count * line_h
        return max(36, page_usable - used - sig_h - footer_gap)
