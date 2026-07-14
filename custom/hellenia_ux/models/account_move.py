from odoo import _, api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    hellenia_show_origin_ncf = fields.Boolean(
        compute="_compute_hellenia_show_origin_ncf",
    )
    hellenia_ret_isr_gov = fields.Boolean(string="Gobierno 5%")
    hellenia_ret_itbis_30 = fields.Boolean(string="ITBIS retenido 30%")
    hellenia_ret_isr_10 = fields.Boolean(string="Proveedor informal 10%")
    hellenia_ret_itbis_75 = fields.Boolean(string="ITBIS informal 75%")
    hellenia_fx_rate_missing = fields.Boolean(
        string="Falta tasa de cambio",
        compute="_compute_hellenia_fx_rate_warning",
    )
    hellenia_fx_rate_warning = fields.Char(
        compute="_compute_hellenia_fx_rate_warning",
    )

    @api.depends("currency_id", "company_id", "invoice_date", "date")
    def _compute_hellenia_fx_rate_warning(self):
        Rate = self.env["res.currency.rate"]
        for move in self:
            move.hellenia_fx_rate_missing = False
            move.hellenia_fx_rate_warning = False
            if move.move_type == "entry":
                continue
            currency = move.currency_id
            company = move.company_id
            if not currency or not company or currency == company.currency_id:
                continue
            ref_date = move.invoice_date or move.date or fields.Date.context_today(move)
            rate = Rate.search(
                [
                    ("currency_id", "=", currency.id),
                    ("company_id", "=", company.id),
                    ("name", "<=", ref_date),
                ],
                order="name desc",
                limit=1,
            )
            if not rate:
                move.hellenia_fx_rate_missing = True
                move.hellenia_fx_rate_warning = _(
                    "No hay tasa de cambio registrada para %(currency)s en la fecha %(date)s. "
                    "Vaya a Contabilidad → Configuración → Tasas de cambio, registre la tasa del día "
                    "y vuelva a abrir este documento.",
                    currency=currency.name,
                    date=ref_date,
                )

    @api.depends("move_type")
    def _compute_hellenia_show_origin_ncf(self):
        for move in self:
            move.hellenia_show_origin_ncf = move.move_type in ("out_refund", "in_refund")

    def action_open_void_ncf_wizard(self):
        """Delegar al wizard canónico de justech_l10n_do_ncf (sin lógica propia)."""
        return super().action_open_void_ncf_wizard()

    def _hellenia_get_withholding_tax(self, name, tax_use):
        return self.env["account.tax"].search(
            [
                ("name", "=", name),
                ("type_tax_use", "=", tax_use),
                ("company_id", "=", self.company_id.id),
            ],
            limit=1,
        )

    @api.onchange(
        "hellenia_ret_isr_gov",
        "hellenia_ret_itbis_30",
        "hellenia_ret_isr_10",
        "hellenia_ret_itbis_75",
    )
    def _onchange_hellenia_withholdings(self):
        for move in self:
            if move.move_type not in ("in_invoice", "in_refund", "out_invoice", "out_refund"):
                continue
            taxes = self.env["account.tax"]
            if move.move_type in ("out_invoice", "out_refund") and move.hellenia_ret_isr_gov:
                taxes |= move._hellenia_get_withholding_tax("-5% ISR Gov.", "sale")
            if move.move_type in ("in_invoice", "in_refund"):
                if move.hellenia_ret_itbis_30:
                    taxes |= move._hellenia_get_withholding_tax("-30% ITBIS Leg. (N02-05)", "purchase")
                if move.hellenia_ret_isr_10:
                    taxes |= move._hellenia_get_withholding_tax("-10% ISR Fee", "purchase")
                if move.hellenia_ret_itbis_75:
                    taxes |= move._hellenia_get_withholding_tax("-75% ITBIS (N08-10)", "purchase")
            for line in move.invoice_line_ids:
                base = line.tax_ids.filtered(lambda t: t.amount >= 0)
                line.tax_ids = base | taxes
