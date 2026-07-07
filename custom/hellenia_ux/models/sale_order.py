from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    hellenia_fx_rate_missing = fields.Boolean(
        string="Falta tasa de cambio",
        compute="_compute_hellenia_fx_rate_warning",
    )
    hellenia_fx_rate_warning = fields.Char(
        compute="_compute_hellenia_fx_rate_warning",
    )

    @api.depends("currency_id", "company_id", "date_order")
    def _compute_hellenia_fx_rate_warning(self):
        Rate = self.env["res.currency.rate"]
        for order in self:
            order.hellenia_fx_rate_missing = False
            order.hellenia_fx_rate_warning = False
            currency = order.currency_id
            company = order.company_id
            if not currency or not company or currency == company.currency_id:
                continue
            ref_date = fields.Date.to_date(order.date_order) or fields.Date.context_today(order)
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
                order.hellenia_fx_rate_missing = True
                order.hellenia_fx_rate_warning = _(
                    "No hay tasa de cambio registrada para %(currency)s en la fecha %(date)s. "
                    "Vaya a Contabilidad → Configuración → Tasas de cambio, registre la tasa del día "
                    "y vuelva a abrir este documento.",
                    currency=currency.name,
                    date=ref_date,
                )
