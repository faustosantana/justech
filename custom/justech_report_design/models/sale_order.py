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
        lines = self._jt_quotation_reportable_lines()
        return any((l.discount or 0) > 0 for l in lines)

    def _jt_quotation_reportable_lines(self):
        self.ensure_one()
        return self._get_order_lines_to_report().filtered(
            lambda l: not l.display_type and not l.is_downpayment
        )

    def _jt_quotation_page_stats(self):
        self.ensure_one()
        lines = self._jt_quotation_reportable_lines()
        count = len(lines)
        lines_per_page = 22
        last_page_lines = count % lines_per_page or (lines_per_page if count >= lines_per_page else count)
        if count < lines_per_page:
            last_page_lines = count
        return count, last_page_lines

    def get_jt_quotation_signature_spacer_px(self):
        """Spacer entre condiciones y firmas (flujo multipágina densa)."""
        self.ensure_one()
        count, last_page_lines = self._jt_quotation_page_stats()
        if count > 22 and last_page_lines > 10:
            return 24
        return 0

    def get_jt_quotation_signature_push_px(self):
        """Fila expansora invisible que empuja firmas al pie en wkhtmltopdf."""
        self.ensure_one()
        if not self.get_jt_quotation_anchor_signatures():
            return self.get_jt_quotation_signature_spacer_px()
        lower_h = self.get_jt_quotation_lower_min_height_px()
        cond_h = 135
        sig_h = 88
        return max(72, lower_h - cond_h - sig_h)

    def get_jt_quotation_lower_min_height_px(self):
        """Altura zona inferior = espacio restante de página para anclar firmas al pie."""
        self.ensure_one()
        count, last_page_lines = self._jt_quotation_page_stats()
        page_usable = 980
        sig_h = 88
        footer_gap = 36
        cond_h = 135
        min_lower = cond_h + sig_h + 72

        if count <= 22:
            fixed_above = 420
            line_h = 34
            content_above_lower = fixed_above + count * line_h
        else:
            if last_page_lines > 10:
                return 0
            content_above_lower = last_page_lines * 34 + 100

        remaining = page_usable - content_above_lower - footer_gap
        return max(min_lower, remaining)

    def get_jt_quotation_anchor_signatures(self):
        """Anclar firmas al pie cuando la última página tiene poco contenido."""
        self.ensure_one()
        count, last_page_lines = self._jt_quotation_page_stats()
        if count <= 22:
            return True
        return last_page_lines <= 10
