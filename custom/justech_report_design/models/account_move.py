# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from odoo import _, models
from odoo.tools import formatLang, is_html_empty


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "jt.delivery.report.mixin"]

    def _jt_invoice_product_lines(self):
        self.ensure_one()
        return self.invoice_line_ids.filtered(
            lambda l: l.display_type in (False, "product")
        )

    def get_jt_payment_term_display(self):
        """Etiqueta española: Contado o Crédito a X días."""
        self.ensure_one()
        term = self.invoice_payment_term_id
        if not term:
            return "Contado"
        days = [int(d) for d in term.line_ids.mapped("nb_days") if d is not None]
        max_days = max(days) if days else 0
        name = (term.name or "").strip().lower()
        if max_days <= 0 or "immediate" in name or "contado" in name or "cash" in name:
            return "Contado"
        return f"Crédito a {max_days} días"

    def format_jt_monetary(self, amount):
        self.ensure_one()
        return formatLang(self.env, amount, currency_obj=self.currency_id)

    def get_jt_invoice_has_discount(self):
        self.ensure_one()
        lines = self._jt_invoice_product_lines()
        return any((l.discount or 0) > 0 for l in lines)

    def get_jt_invoice_gross_subtotal(self):
        self.ensure_one()
        lines = self._jt_invoice_product_lines()
        return sum(l.quantity * l.price_unit for l in lines)

    def get_jt_invoice_discount_total(self):
        self.ensure_one()
        gross = self.get_jt_invoice_gross_subtotal()
        discount = gross - self.amount_untaxed
        currency = self.currency_id
        if currency:
            discount = currency.round(discount)
        return discount if discount > 0 else 0.0

    def get_jt_invoice_show_discount_totals(self):
        self.ensure_one()
        return self.get_jt_invoice_discount_total() > 0

    def get_jt_line_discount_amount(self, line):
        qty = line.quantity or 0.0
        price = line.price_unit or 0.0
        disc = line.discount or 0.0
        amount = qty * price * disc / 100.0
        return line.currency_id.round(amount) if line.currency_id else amount

    def _jt_is_itbis_tax(self, tax):
        if not tax:
            return False
        name = (tax.name or "").upper()
        if "ITBIS" in name or "IVA" in name:
            return True
        return (tax.amount or 0) > 0 and tax.amount in (18.0, 16.0, 9.0, 8.0)

    def _jt_is_withholding_tax(self, tax):
        return bool(tax and (tax.amount or 0) < 0)

    def get_jt_line_itbis_amount(self, line):
        self.ensure_one()
        taxes = line.tax_ids.flatten_taxes_hierarchy().filtered(self._jt_is_itbis_tax)
        if not taxes:
            return 0.0
        base = line.price_subtotal
        total = 0.0
        for tax in taxes:
            if tax.amount_type == "percent":
                total += base * tax.amount / 100.0
            elif tax.amount_type == "fixed":
                total += tax.amount * (line.quantity or 0.0)
        return line.currency_id.round(total) if line.currency_id else total

    def get_jt_invoice_itbis_total(self):
        self.ensure_one()
        total = 0.0
        if self.state == "posted":
            FiscalReport = self.env.get("justech.do.fiscal.report")
            if FiscalReport:
                total = FiscalReport._move_itbis_amount(self)
        if not total:
            lines = self._jt_invoice_product_lines()
            total = sum(self.get_jt_line_itbis_amount(line) for line in lines)
        if not total and self.amount_total > self.amount_untaxed:
            ret_total = sum(r["amount"] for r in self.get_jt_invoice_retention_lines())
            total = self.amount_total - self.amount_untaxed + ret_total
            if total < 0:
                total = 0.0
        return self.currency_id.round(total) if self.currency_id else total

    def get_jt_invoice_retention_lines(self):
        """Lista de dicts {label, amount} para retenciones en factura."""
        self.ensure_one()
        result = []
        if self.state == "posted":
            for line in self.line_ids.filtered(
                lambda l: l.tax_line_id and self._jt_is_withholding_tax(l.tax_line_id)
            ):
                tax = line.tax_line_id
                amount = abs(line.balance)
                if amount:
                    result.append({
                        "label": tax.name or "Retención",
                        "amount": amount,
                    })
        else:
            taxes = self._jt_invoice_product_lines().mapped("tax_ids").flatten_taxes_hierarchy()
            for tax in taxes.filtered(self._jt_is_withholding_tax):
                base = self.amount_untaxed
                amount = abs(base * tax.amount / 100.0) if tax.amount_type == "percent" else abs(tax.amount)
                if amount:
                    result.append({"label": tax.name or "Retención", "amount": amount})
        return result

    def get_jt_invoice_show_retentions(self):
        self.ensure_one()
        return bool(self.get_jt_invoice_retention_lines())

    def get_jt_invoice_number_display(self):
        """Número visible en banda verde (sin inventar NCF)."""
        self.ensure_one()
        name = (self.name or "").strip()
        if name and name not in ("/", "False"):
            return name
        if self.state == "draft":
            return _("Borrador")
        return "—"

    def get_jt_invoice_band_title(self):
        """Título banda verde según tipo de documento."""
        self.ensure_one()
        if self.move_type == "out_refund":
            return "NOTA DE CRÉDITO"
        doc_type = getattr(self, "justech_do_document_type_id", False)
        if doc_type and getattr(doc_type, "is_debit_note", False):
            return "NOTA DE DÉBITO"
        return "FACTURA"

    def get_jt_document_type_label(self):
        self.ensure_one()
        doc_type = getattr(self, "justech_do_document_type_id", False)
        if not doc_type and hasattr(self, "_justech_resolve_document_type"):
            doc_type = self._justech_resolve_document_type()
        if doc_type:
            return doc_type.name or "—"
        return "—"

    def get_jt_document_type_short_display(self):
        """Nombre comercial corto para banda fiscal (solo presentación PDF)."""
        self.ensure_one()
        full = (self.get_jt_document_type_label() or "").strip()
        if not full or full == "—":
            return "—"
        if full == "Factura de Consumo":
            return "Consumidor Final"
        if full.startswith("Factura de "):
            return full[len("Factura de "):]
        if full.startswith("Factura "):
            return full[len("Factura "):]
        if full.startswith("Comprobante de "):
            return full[len("Comprobante de "):]
        return full

    def get_jt_ncf_display(self):
        self.ensure_one()
        ncf = getattr(self, "justech_do_ncf", "") or ""
        return ncf if ncf else "—"

    def get_jt_currency_display(self):
        self.ensure_one()
        if self.currency_id:
            return self.currency_id.name or "—"
        return "—"

    def get_jt_invoice_date_display(self):
        self.ensure_one()
        if self.invoice_date:
            return self.invoice_date.strftime("%d/%m/%Y")
        return "—"

    def get_jt_invoice_due_date_display(self):
        self.ensure_one()
        if self.invoice_date_due:
            return self.invoice_date_due.strftime("%d/%m/%Y")
        return "—"

    def jt_show_invoice_observations(self):
        self.ensure_one()
        if not is_html_empty(self.narration):
            return True
        company = self.company_id
        if company and hasattr(company, "hellenia_terms_conditions"):
            return not is_html_empty(company.hellenia_terms_conditions)
        return False

    def jt_invoice_observations_html(self):
        """Contenido HTML para bloque observaciones."""
        self.ensure_one()
        if not is_html_empty(self.narration):
            return self.narration
        company = self.company_id
        if company and hasattr(company, "hellenia_terms_conditions"):
            return company.hellenia_terms_conditions
        return False

    def get_jt_partner_address_display(self):
        self.ensure_one()
        partner = self.partner_id
        parts = []
        if partner.street:
            parts.append(partner.street)
        if partner.street2:
            parts.append(partner.street2)
        city_parts = [p for p in (partner.city, partner.state_id.name if partner.state_id else "") if p]
        if city_parts:
            parts.append(", ".join(city_parts))
        return ", ".join(parts)

    def _jt_delivery_related_sale_order(self):
        self.ensure_one()
        if self.invoice_origin:
            so = self.env["sale.order"].search(
                [
                    ("name", "=", self.invoice_origin),
                    ("company_id", "=", self.company_id.id),
                ],
                limit=1,
            )
            if so:
                return so
        orders = self.invoice_line_ids.mapped("sale_line_ids.order_id")
        return orders[:1]

    def get_jt_delivery_conduce_number(self):
        so = self._jt_delivery_related_sale_order()
        if so:
            return so.get_jt_delivery_conduce_number()
        return self._jt_delivery_dash(self.name)

    def get_jt_delivery_picking_number(self):
        so = self._jt_delivery_related_sale_order()
        if so:
            return so.get_jt_delivery_picking_number()
        return "—"

    def get_jt_delivery_sale_order_name(self):
        so = self._jt_delivery_related_sale_order()
        return self._jt_delivery_dash(so.name if so else False)

    def get_jt_delivery_invoice_name(self):
        if self.move_type == "out_invoice" and self.name:
            return self._jt_delivery_dash(self.name)
        return "—"

    def get_jt_delivery_state_display(self):
        return self._jt_delivery_state_label_invoice(self.state)

    def get_jt_delivery_date_display(self):
        so = self._jt_delivery_related_sale_order()
        if so:
            return so.get_jt_delivery_date_display()
        if self.invoice_date:
            return self.invoice_date.strftime("%d/%m/%Y")
        return "—"

    def get_jt_delivery_customer_name(self):
        return self.partner_id.name if self.partner_id else "—"

    def get_jt_delivery_shipping_address(self):
        partner = self.partner_shipping_id or self.partner_id
        return self._jt_delivery_format_address(partner)

    def get_jt_delivery_responsible_display(self):
        return self.invoice_user_id.name if self.invoice_user_id else "—"

    def get_jt_delivery_salesperson_display(self):
        return self.invoice_user_id.name if self.invoice_user_id else "—"

    def get_jt_delivery_carrier_display(self):
        so = self._jt_delivery_related_sale_order()
        if so:
            return so.get_jt_delivery_carrier_display()
        return "—"

    def get_jt_delivery_warehouse_origin(self):
        so = self._jt_delivery_related_sale_order()
        if so:
            return so.get_jt_delivery_warehouse_origin()
        return "—"

    def get_jt_delivery_destination_location(self):
        so = self._jt_delivery_related_sale_order()
        if so:
            return so.get_jt_delivery_destination_location()
        return "—"

    def get_jt_delivery_observations_html(self):
        return self.narration or False

    def get_jt_delivery_lines(self):
        self.ensure_one()
        lines = []
        for line in self._jt_invoice_product_lines().sorted(key=lambda l: l.sequence):
            product = line.product_id
            code = product.default_code if product else ""
            qty = line.quantity
            lines.append(
                self._jt_delivery_line_dict(
                    code,
                    line.name,
                    qty,
                    qty,
                    line.product_uom_id.name if line.product_uom_id else "",
                    "",
                )
            )
        return lines
