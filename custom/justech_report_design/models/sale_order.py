# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from markupsafe import Markup

from odoo import api, models
from odoo.tools import formatLang, html_escape, is_html_empty


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def _jt_company_terms_as_note_html(self, company):
        """Texto plano de empresa → HTML para sale.order.note (sin fallback en PDF)."""
        if not company:
            return False
        terms = (company.hellenia_quotation_terms or "").strip()
        if not terms:
            return False
        return Markup("<p>") + Markup(html_escape(terms).replace("\n", "<br/>")) + Markup("</p>")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if "note" in fields_list and is_html_empty(res.get("note")):
            company = self.env.company
            if res.get("company_id"):
                company = self.env["res.company"].browse(res["company_id"])
            note_html = self._jt_company_terms_as_note_html(company)
            if note_html:
                res["note"] = note_html
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if is_html_empty(vals.get("note")):
                company = self.env["res.company"].browse(
                    vals.get("company_id") or self.env.company.id
                )
                note_html = self._jt_company_terms_as_note_html(company)
                if note_html:
                    vals["note"] = note_html
        return super().create(vals_list)

    def jt_show_quotation_conditions(self):
        """True si la cotización tiene condiciones en note (bloque PDF)."""
        self.ensure_one()
        return not is_html_empty(self.note)

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
