# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from odoo import models
from odoo.tools import formatLang, html2plaintext, is_html_empty


class SaleOrder(models.Model):
    _inherit = "sale.order"

    _JT_DEFAULT_TERMS = """(a) Las piezas ofrecidas son únicas y sujetas a disponibilidad.
(b) Esta cotización tiene una validez de 5 días.
(c) Se requiere confirmación del pago del 100% para reservar la pieza.
(d) Transporte disponible bajo cotización.
(e) Asesoría de colocación, instalación y styling disponible bajo cotización.
(f) Las piezas pueden presentar marcas propias del tiempo, lo cual forma parte de su carácter y autenticidad."""

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

    def _jt_quotation_reportable_lines(self):
        self.ensure_one()
        return self._get_order_lines_to_report().filtered(
            lambda l: not l.display_type and not l.is_downpayment
        )

    def get_jt_quotation_has_discount(self):
        """True si alguna línea reportable tiene descuento > 0."""
        self.ensure_one()
        lines = self._jt_quotation_reportable_lines()
        return any((l.discount or 0) > 0 for l in lines)

    def get_jt_quotation_terms_display(self):
        """Condiciones editables desde doc.note; fallback a texto por defecto."""
        self.ensure_one()
        if not is_html_empty(self.note):
            return html2plaintext(self.note).strip()
        return self._JT_DEFAULT_TERMS

    def get_jt_quotation_terms_from_note(self):
        """True si las condiciones provienen de la nota editable de la cotización."""
        self.ensure_one()
        return not is_html_empty(self.note)

    def get_jt_quotation_gross_subtotal(self):
        """Suma qty × precio unitario antes de descuentos de línea."""
        self.ensure_one()
        lines = self._jt_quotation_reportable_lines()
        return sum(l.product_uom_qty * l.price_unit for l in lines)

    def get_jt_quotation_discount_total(self):
        """Monto total de descuento antes de ITBIS."""
        self.ensure_one()
        gross = self.get_jt_quotation_gross_subtotal()
        discount = gross - self.amount_untaxed
        currency = self.currency_id
        if currency:
            discount = currency.round(discount)
        return discount if discount > 0 else 0.0

    def get_jt_quotation_show_discount_totals(self):
        """Mostrar desglose bruto/descuento/subtotal en bloque de totales."""
        self.ensure_one()
        return self.get_jt_quotation_discount_total() > 0

    def format_jt_monetary(self, amount):
        """Formato moneda para totales calculados en QWeb."""
        self.ensure_one()
        return formatLang(self.env, amount, currency_obj=self.currency_id)

    def _jt_quotation_page_stats(self):
        self.ensure_one()
        lines = self._jt_quotation_reportable_lines()
        count = len(lines)
        lines_per_page = 22
        last_page_lines = count % lines_per_page or (lines_per_page if count >= lines_per_page else count)
        if count < lines_per_page:
            last_page_lines = count
        return count, last_page_lines

    def _jt_quotation_conditions_height_px(self):
        """Estimación altura bloque CONDICIONES para cálculo de spacer."""
        self.ensure_one()
        terms = self.get_jt_quotation_terms_display() or ""
        line_count = terms.count("\n") + 1
        return min(240, max(72, 36 + line_count * 13))

    def get_jt_quotation_signature_spacer_px(self):
        """Spacer entre condiciones y firmas (flujo multipágina densa)."""
        self.ensure_one()
        count, last_page_lines = self._jt_quotation_page_stats()
        if count > 22 and last_page_lines > 10:
            return 28
        return 0

    def get_jt_quotation_signature_push_px(self):
        """Espacio flexible condiciones → firmas, sin forzar salto de página."""
        self.ensure_one()
        if not self.get_jt_quotation_anchor_signatures():
            return max(28, self.get_jt_quotation_signature_spacer_px())

        count, last_page_lines = self._jt_quotation_page_stats()
        page_usable = 1090
        sig_h = 82
        footer_gap = 4
        cond_h = self._jt_quotation_conditions_height_px()
        totals_h = 78 if self.get_jt_quotation_show_discount_totals() else 58

        if count <= 22:
            content_above_lower = 412 + count * 34 + totals_h
        else:
            content_above_lower = last_page_lines * 34 + totals_h

        max_push = page_usable - content_above_lower - cond_h - sig_h - footer_gap
        boost = 28 if count <= 5 else (14 if count <= 15 else 0)
        cap = 340 if count <= 5 else 310
        return max(64, min(int(max_push) + boost, cap))

    def get_jt_quotation_lower_min_height_px(self):
        """Compatibilidad — altura mínima zona inferior."""
        self.ensure_one()
        cond_h = self._jt_quotation_conditions_height_px()
        push = self.get_jt_quotation_signature_push_px()
        return cond_h + push + 90

    def get_jt_quotation_anchor_signatures(self):
        """Anclar firmas al pie cuando la última página tiene poco contenido."""
        self.ensure_one()
        count, last_page_lines = self._jt_quotation_page_stats()
        if count <= 22:
            return True
        return last_page_lines <= 10
