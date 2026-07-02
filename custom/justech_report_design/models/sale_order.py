# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from markupsafe import Markup

from odoo import _, api, models
from odoo.tools import formatLang, html_escape, is_html_empty


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "jt.delivery.report.mixin"]

    @api.model
    def _jt_company_terms_as_note_html(self, company):
        """Texto plano de empresa → HTML para sale.order.note (sin fallback en PDF)."""
        if not company:
            return False
        terms = company.jt_get_quotation_terms_text()
        if not terms:
            return False
        return Markup("<p>") + Markup(html_escape(terms).replace("\n", "<br/>")) + Markup("</p>")

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Siempre precargar note si está vacío (Odoo a veces no incluye note en fields_list).
        if is_html_empty(res.get("note")):
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

    @api.model
    def jt_backfill_empty_quotation_notes(self):
        """Rellena note en borradores/enviadas vacías desde condiciones de empresa."""
        orders = self.search([("state", "in", ("draft", "sent"))])
        updated = self.browse()
        for order in orders:
            if is_html_empty(order.note):
                note_html = self._jt_company_terms_as_note_html(order.company_id)
                if note_html:
                    order.note = note_html
                    updated |= order
        return updated

    def _jt_delivery_reportable_lines(self):
        self.ensure_one()
        return self.order_line.filtered(
            lambda l: not l.display_type and not l.is_downpayment and l.product_id
        )

    def _jt_delivery_related_invoices(self):
        self.ensure_one()
        return self.invoice_ids.filtered(
            lambda m: m.move_type == "out_invoice" and m.state == "posted"
        )

    def get_jt_delivery_conduce_number(self):
        pickings = self.picking_ids.filtered(
            lambda p: p.picking_type_code == "outgoing" and p.state != "cancel"
        )
        if pickings:
            return self._jt_delivery_dash(pickings[0].name)
        return self._jt_delivery_dash(self.name)

    def get_jt_delivery_picking_number(self):
        pickings = self.picking_ids.filtered(
            lambda p: p.picking_type_code == "outgoing" and p.state != "cancel"
        )
        if pickings:
            return self._jt_delivery_dash(pickings[0].name)
        return "—"

    def get_jt_delivery_sale_order_name(self):
        return self._jt_delivery_dash(self.name)

    def get_jt_delivery_invoice_name(self):
        invs = self._jt_delivery_related_invoices()
        if not invs:
            return "—"
        return ", ".join(invs.mapped("name")) or "—"

    def get_jt_delivery_state_display(self):
        return self._jt_delivery_state_label_sale(self.state)

    def get_jt_delivery_date_display(self):
        pickings = self.picking_ids.filtered(
            lambda p: p.picking_type_code == "outgoing" and p.state == "done"
        )
        if pickings and pickings[0].date_done:
            return pickings[0].date_done.strftime("%d/%m/%Y")
        if self.commitment_date:
            return self.commitment_date.strftime("%d/%m/%Y")
        if self.date_order:
            return self.date_order.strftime("%d/%m/%Y")
        return "—"

    def get_jt_delivery_customer_name(self):
        return self.partner_id.name if self.partner_id else "—"

    def get_jt_delivery_shipping_address(self):
        lines = self.get_jt_delivery_shipping_address_lines()
        return ", ".join(lines) if lines else "—"

    def _jt_delivery_resolve_shipping_partner(self):
        self.ensure_one()
        candidates = self._jt_delivery_expand_partner_candidates(
            self.partner_shipping_id,
            self.partner_id,
        )
        for partner in candidates:
            if self._jt_delivery_partner_has_address(partner):
                return partner
        return candidates[0] if candidates else self.env["res.partner"]

    def get_jt_delivery_responsible_display(self):
        pickings = self.picking_ids.filtered(
            lambda p: p.picking_type_code == "outgoing" and p.state != "cancel"
        )
        if pickings and pickings[0].user_id:
            return self._jt_delivery_user_label(pickings[0].user_id)
        return "—"

    def get_jt_delivery_salesperson_display(self):
        return self._jt_delivery_user_label(self.user_id)

    def get_jt_delivery_carrier_display(self):
        pickings = self.picking_ids.filtered(lambda p: p.picking_type_code == "outgoing")
        for picking in pickings:
            if picking._fields.get("carrier_id") and picking.carrier_id:
                return picking.carrier_id.name
        return "—"

    def get_jt_delivery_warehouse_origin(self):
        pickings = self.picking_ids.filtered(lambda p: p.picking_type_code == "outgoing")
        if pickings:
            return pickings[0].get_jt_delivery_warehouse_origin()
        return "—"

    def get_jt_delivery_destination_location(self):
        pickings = self.picking_ids.filtered(lambda p: p.picking_type_code == "outgoing")
        if pickings and pickings[0].location_dest_id:
            return pickings[0].location_dest_id.display_name
        return "—"

    def get_jt_delivery_observations_html(self):
        return self.note or False

    def get_jt_delivery_lines(self):
        self.ensure_one()
        lines = []
        for line in self._jt_delivery_reportable_lines().sorted(key=lambda l: l.sequence):
            product = line.product_id
            code = product.default_code or ""
            qty_req = line.product_uom_qty
            qty_del = line.qty_delivered if "qty_delivered" in line._fields else qty_req
            lines.append(
                self._jt_delivery_line_dict(
                    code,
                    line.name,
                    qty_req,
                    qty_del,
                    line.product_uom_id.name if line.product_uom_id else "",
                    "",
                )
            )
        return lines

    def _jt_delivery_outgoing_pickings(self):
        self.ensure_one()
        return self.picking_ids.filtered(
            lambda p: p.picking_type_code == "outgoing" and p.state != "cancel"
        )

    @api.depends(
        "picking_ids",
        "picking_ids.state",
        "picking_ids.picking_type_code",
    )
    def _compute_jt_delivery_ui(self):
        return super()._compute_jt_delivery_ui()

    def _jt_delivery_document_kind_label(self):
        self.ensure_one()
        if self.state in ("draft", "sent"):
            return _("cotización")
        return _("orden de venta")

    def _jt_delivery_document_reference(self):
        return self.name or self.display_name

    def action_jt_print_delivery_conduce(self):
        self.ensure_one()
        pickings = self._jt_delivery_outgoing_pickings()
        used_picking = False
        if len(pickings) == 1:
            report = self.env.ref(self._jt_delivery_picking_report_xmlid())
            target = pickings
            used_picking = True
        else:
            report = self.env.ref(self._jt_delivery_sale_report_xmlid())
            target = self
        self._jt_delivery_post_print_message(pickings, used_picking_report=used_picking)
        return report.report_action(target)
