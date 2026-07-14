# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.tools import formatLang, is_html_empty


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def _jt_po_reportable_lines(self):
        self.ensure_one()
        return self.order_line.filtered(lambda l: not l.display_type and l.product_id)

    def format_jt_monetary(self, amount):
        self.ensure_one()
        return formatLang(self.env, amount, currency_obj=self.currency_id)

    def format_jt_discount_percent(self, discount):
        value = discount or 0
        if value == int(value):
            return f"{int(value)}%"
        return f"{value:g}%"

    def get_jt_po_has_discount(self):
        self.ensure_one()
        return any((l.discount or 0) > 0 for l in self._jt_po_reportable_lines())

    def get_jt_po_gross_subtotal(self):
        self.ensure_one()
        lines = self._jt_po_reportable_lines()
        return sum(l.product_qty * l.price_unit for l in lines)

    def get_jt_po_discount_total(self):
        self.ensure_one()
        gross = self.get_jt_po_gross_subtotal()
        discount = gross - self.amount_untaxed
        currency = self.currency_id
        if currency:
            discount = currency.round(discount)
        return discount if discount > 0 else 0.0

    def get_jt_po_show_discount_totals(self):
        self.ensure_one()
        return self.get_jt_po_discount_total() > 0

    def get_jt_line_discount_amount(self, line):
        qty = line.product_qty or 0.0
        price = line.price_unit or 0.0
        disc = line.discount or 0.0
        amount = qty * price * disc / 100.0
        return line.currency_id.round(amount) if line.currency_id else amount

    def get_jt_line_tax_display(self, line):
        taxes = line.tax_ids
        if not taxes:
            return "—"
        names = [t.name for t in taxes if t.name]
        return ", ".join(names) if names else "—"

    def get_jt_po_band_title(self):
        """Título dinámico PURCHASE-UX-1: RFQ vs Orden de Compra."""
        self.ensure_one()
        if self.state in ("draft", "sent"):
            return _("SOLICITUD DE ORDEN")
        if self.state in ("purchase", "done"):
            return _("ORDEN DE COMPRA")
        if self.state == "to approve":
            return _("SOLICITUD DE ORDEN")
        if self.state == "cancel":
            return _("ORDEN DE COMPRA")
        return _("ORDEN DE COMPRA")

    def get_jt_po_is_rfq_document(self):
        self.ensure_one()
        return self.state in ("draft", "sent", "to approve")

    def get_jt_po_number_prefix(self):
        self.ensure_one()
        if self.get_jt_po_is_rfq_document():
            return _("No.")
        return _("No.")

    def get_jt_po_date_label(self):
        self.ensure_one()
        if self.get_jt_po_is_rfq_document():
            return _("Fecha de solicitud:")
        return _("Fecha de orden:")

    def get_jt_po_validity_display(self):
        """Validez solo si el campo existe en el modelo (p. ej. extensiones futuras)."""
        self.ensure_one()
        validity = getattr(self, "validity_date", False)
        if validity:
            return fields.Date.to_date(validity).strftime("%d/%m/%Y")
        return False

    def get_jt_po_company_display(self):
        self.ensure_one()
        return self.company_id.display_name if self.company_id else "—"

    def get_jt_po_show_expected_date(self):
        self.ensure_one()
        return self.state in ("purchase", "done") and bool(
            self.get_jt_po_expected_date_display() != "—"
        )

    def get_jt_po_state_display(self):
        self.ensure_one()
        labels = {
            "draft": "Borrador",
            "sent": "Enviada",
            "to approve": "Por aprobar",
            "purchase": "Orden de compra",
            "done": "Bloqueada",
            "cancel": "Cancelada",
        }
        return labels.get(self.state, self.state or "—")

    def get_jt_po_currency_display(self):
        self.ensure_one()
        if self.currency_id:
            return self.currency_id.name or self.currency_id.display_name
        return "—"

    def get_jt_po_order_date_display(self):
        self.ensure_one()
        if not self.date_order:
            return "—"
        dt = fields.Datetime.to_datetime(self.date_order)
        return dt.strftime("%d/%m/%Y") if dt else "—"

    def get_jt_po_expected_date_display(self):
        self.ensure_one()
        dt = self.date_planned
        if not dt:
            lines = self._jt_po_reportable_lines()
            dates = [l.date_planned for l in lines if l.date_planned]
            dt = min(dates) if dates else False
        if not dt:
            return "—"
        dt = fields.Datetime.to_datetime(dt)
        return dt.strftime("%d/%m/%Y") if dt else "—"

    def get_jt_po_buyer_display(self):
        self.ensure_one()
        return self.user_id.name if self.user_id else "—"

    def get_jt_payment_term_display(self):
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

    def get_jt_po_incoterm_display(self):
        self.ensure_one()
        if not self.incoterm_id:
            return "—"
        code = (self.incoterm_id.code or "").strip()
        if self.incoterm_location:
            return f"{code} — {self.incoterm_location}" if code else self.incoterm_location
        return code or self.incoterm_id.name or "—"

    def get_jt_partner_address_lines(self, partner=None):
        self.ensure_one()
        partner = partner or self.partner_id
        if not partner:
            return []
        lines = []
        street_parts = [p for p in (partner.street, partner.street2) if p]
        if street_parts:
            lines.append(", ".join(street_parts))
        city_parts = [
            p
            for p in (
                partner.city,
                partner.state_id.name if partner.state_id else "",
            )
            if p
        ]
        if city_parts:
            lines.append(" / ".join(city_parts))
        if partner.country_id and partner.country_id.name:
            if not lines or partner.country_id.name not in " / ".join(lines):
                lines.append(partner.country_id.name)
        return lines

    def get_jt_po_vendor_partner(self):
        self.ensure_one()
        return self.dest_address_id or self.partner_id

    def jt_show_po_observations(self):
        self.ensure_one()
        return not is_html_empty(self.note)

    @api.readonly
    def action_preview_purchase_order(self):
        """Vista previa nativa — portal con iframe, volver/imprimir/descargar."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "target": "self",
            "url": self.get_portal_url(suffix="/preview"),
        }

    def get_jt_po_preview_portal_url(self):
        self.ensure_one()
        return self.get_portal_url(suffix="/preview")
