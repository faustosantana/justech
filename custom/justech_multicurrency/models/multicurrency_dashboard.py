from odoo import api, fields, models


class JustechMulticurrencyDashboard(models.TransientModel):
    _name = "justech.multicurrency.dashboard"
    _description = "Dashboard Multimoneda Justech"

    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    policy_id = fields.Many2one("justech.multicurrency.policy", string="Política")

    accounting_currency_id = fields.Many2one("res.currency", compute="_compute_snapshot", string="Moneda contable")
    commercial_currency_id = fields.Many2one("res.currency", compute="_compute_snapshot", string="Moneda comercial")
    default_pricelist_id = fields.Many2one("product.pricelist", compute="_compute_snapshot", string="Lista pública")
    pricelist_count = fields.Integer(compute="_compute_snapshot", string="Cantidad de listas")
    last_rate_date = fields.Date(compute="_compute_snapshot", string="Fecha última tasa")
    last_rate_datetime = fields.Datetime(compute="_compute_snapshot", string="Registro")
    last_rate_user_id = fields.Many2one("res.users", compute="_compute_snapshot", string="Usuario")
    last_rate_origin = fields.Char(compute="_compute_snapshot", string="Origen")
    last_rate_value = fields.Float(compute="_compute_snapshot", digits=(16, 6), string="Valor tasa")
    last_rate_currency_id = fields.Many2one("res.currency", compute="_compute_snapshot", string="Moneda tasa")
    summary_html = fields.Html(compute="_compute_snapshot", sanitize=False, string="Resumen")

    @api.depends("company_id", "policy_id")
    def _compute_snapshot(self):
        Rate = self.env["res.currency.rate"]
        for dash in self:
            company = dash.company_id or dash.env.company
            policy = dash.policy_id or dash.env["justech.multicurrency.policy"].get_policy(company)
            dash.accounting_currency_id = policy.accounting_currency_id
            dash.commercial_currency_id = policy.commercial_currency_id
            dash.default_pricelist_id = policy.default_pricelist_id
            dash.pricelist_count = policy.pricelist_count

            commercial = policy.commercial_currency_id
            accounting = policy.accounting_currency_id
            rate_rec = False
            if commercial and accounting and commercial != accounting:
                rate_rec = Rate.search(
                    [
                        ("currency_id", "=", commercial.id),
                        ("company_id", "in", [company.id, False]),
                        ("justech_archived", "=", False),
                    ],
                    order="name desc, id desc",
                    limit=1,
                )
            dash.last_rate_currency_id = commercial if rate_rec else False
            dash.last_rate_date = rate_rec.name if rate_rec else False
            dash.last_rate_datetime = rate_rec.create_date if rate_rec else False
            dash.last_rate_user_id = rate_rec.create_uid if rate_rec else False
            dash.last_rate_origin = rate_rec.justech_rate_origin if rate_rec else False
            dash.last_rate_value = rate_rec.inverse_company_rate if rate_rec else 0.0

            pl_name = dash.default_pricelist_id.display_name if dash.default_pricelist_id else "—"
            dash.summary_html = (
                f"<div class='justech_mc_dashboard'>"
                f"<p><strong>Empresa:</strong> {company.display_name}</p>"
                f"<p><strong>Contable:</strong> {dash.accounting_currency_id.name or '—'}"
                f" &nbsp;|&nbsp; <strong>Comercial:</strong> {dash.commercial_currency_id.name or '—'}</p>"
                f"<p><strong>Lista pública:</strong> {pl_name}"
                f" &nbsp;|&nbsp; <strong>Listas totales:</strong> {dash.pricelist_count}</p>"
                f"</div>"
            )

    @api.model
    def action_open(self):
        dashboard = self.create({})
        return {
            "type": "ir.actions.act_window",
            "name": "Dashboard Multimoneda",
            "res_model": self._name,
            "res_id": dashboard.id,
            "view_mode": "form",
            "target": "current",
        }
