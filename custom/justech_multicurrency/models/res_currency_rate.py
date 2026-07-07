from odoo import api, fields, models


class ResCurrencyRate(models.Model):
    _inherit = "res.currency.rate"

    justech_rate_origin = fields.Selection(
        selection=[
            ("manual", "Manual"),
            ("import", "Importación"),
            ("api", "API / Automático"),
            ("system", "Sistema"),
        ],
        string="Origen Justech",
        default="manual",
        index=True,
        help="Origen administrativo registrado por el motor Justech. "
        "No altera el cálculo estándar de Odoo.",
    )
    justech_archived = fields.Boolean(
        string="Archivada (Justech)",
        default=False,
        index=True,
        help="Oculta la tasa en la administración activa Justech. "
        "El motor contable Odoo sigue usando tasas por fecha.",
    )

    def action_justech_archive_rate(self):
        for rate in self:
            rate.justech_archived = True

    def action_justech_restore_rate(self):
        for rate in self:
            rate.justech_archived = False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._justech_resync_product_prices()
        return records

    def write(self, vals):
        res = super().write(vals)
        if {"rate", "currency_id", "justech_archived", "inverse_company_rate"} & set(vals):
            self._justech_resync_product_prices()
        return res

    def _justech_resync_product_prices(self):
        Template = self.env["product.template"]
        for rate in self:
            if rate.justech_archived:
                continue
            Template.with_context(
                justech_sync_sale=True,
                justech_sync_purchase=True,
            )._justech_resync_for_currency(rate.currency_id)
