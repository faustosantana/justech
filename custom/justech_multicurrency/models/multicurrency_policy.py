from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class JustechMulticurrencyPolicy(models.Model):
    _name = "justech.multicurrency.policy"
    _description = "Política Comercial Multimoneda Justech"
    _rec_name = "company_id"
    _order = "company_id"

    company_id = fields.Many2one(
        "res.company",
        string="Empresa",
        required=True,
        ondelete="cascade",
        default=lambda self: self.env.company,
    )
    commercial_currency_id = fields.Many2one(
        "res.currency",
        string="Moneda comercial principal",
        required=True,
        help="Moneda de referencia para la operación comercial (listas, defaults).",
    )
    accounting_currency_id = fields.Many2one(
        "res.currency",
        string="Moneda contable",
        related="company_id.currency_id",
        readonly=True,
        help="Moneda funcional de la empresa (Odoo estándar). Solo lectura.",
    )
    default_pricelist_id = fields.Many2one(
        "product.pricelist",
        string="Lista de precios por defecto",
        domain="[('company_id', 'in', [company_id, False])]",
        help="Lista asignada por defecto a nuevos clientes.",
    )
    default_customer_currency_id = fields.Many2one(
        "res.currency",
        string="Moneda por defecto — clientes",
        help="Moneda comercial esperada en ventas para nuevos clientes.",
    )
    default_supplier_currency_id = fields.Many2one(
        "res.currency",
        string="Moneda por defecto — proveedores",
        help="Moneda por defecto en compras para nuevos proveedores.",
    )
    default_product_pricelist_id = fields.Many2one(
        "product.pricelist",
        string="Lista comercial — productos nuevos",
        domain="[('company_id', 'in', [company_id, False])]",
        help="Lista donde se registra automáticamente el precio comercial de cada producto.",
    )
    pricelist_count = fields.Integer(compute="_compute_pricelist_count", string="Listas activas")
    notes = fields.Text(string="Notas")

    _company_uniq = models.Constraint(
        "unique(company_id)",
        "Solo puede existir una política multimoneda por empresa.",
    )

    @api.depends("company_id")
    def _compute_pricelist_count(self):
        Pricelist = self.env["product.pricelist"]
        for policy in self:
            domain = [("company_id", "in", [policy.company_id.id, False])] if policy.company_id else []
            policy.pricelist_count = Pricelist.search_count(domain) if domain else 0

    @api.constrains(
        "commercial_currency_id",
        "default_pricelist_id",
        "default_product_pricelist_id",
        "company_id",
    )
    def _check_pricelist_currency_alignment(self):
        for policy in self:
            for pl_field, pl in (
                ("default_pricelist_id", policy.default_pricelist_id),
                ("default_product_pricelist_id", policy.default_product_pricelist_id),
            ):
                if not pl or not pl.currency_id or not policy.commercial_currency_id:
                    continue
                if pl.currency_id != policy.commercial_currency_id:
                    raise ValidationError(
                        _(
                            "La lista %(list)s debe usar la moneda comercial %(currency)s.",
                            list=pl.display_name,
                            currency=policy.commercial_currency_id.display_name,
                        )
                    )

    @api.model
    def get_policy(self, company=None):
        company = company or self.env.company
        policy = self.search([("company_id", "=", company.id)], limit=1)
        if not policy:
            policy = self.create_default_for_company(company)
        return policy

    @api.model
    def create_default_for_company(self, company):
        currency = company.currency_id
        pricelist = self._find_or_create_public_pricelist(company, currency)
        return self.create(
            {
                "company_id": company.id,
                "commercial_currency_id": currency.id,
                "default_pricelist_id": pricelist.id,
                "default_customer_currency_id": currency.id,
                "default_supplier_currency_id": currency.id,
                "default_product_pricelist_id": pricelist.id,
            }
        )

    @api.model
    def convert_to_company_currency(self, amount, from_currency, company=None, date=None):
        """Convierte un monto comercial a moneda funcional usando tasas estándar Odoo."""
        company = company or self.env.company
        date = date or fields.Date.today()
        if not from_currency or from_currency == company.currency_id:
            return amount
        Rate = self.env["res.currency.rate"].sudo()
        rate_rec = Rate.search(
            [
                ("currency_id", "=", from_currency.id),
                ("name", "<=", date),
                ("company_id", "in", [company.id, False]),
                ("justech_archived", "=", False),
            ],
            order="name desc, id desc",
            limit=1,
        )
        if not rate_rec:
            rate_rec = Rate.search(
                [
                    ("currency_id", "=", from_currency.id),
                    ("name", "<=", date),
                    ("company_id", "in", [company.id, False]),
                ],
                order="name desc, id desc",
                limit=1,
            )
        if rate_rec and rate_rec.inverse_company_rate:
            return amount * rate_rec.inverse_company_rate
        return from_currency._convert(amount, company.currency_id, company, date)

    @api.model
    def _find_or_create_public_pricelist(self, company, currency):
        Pricelist = self.env["product.pricelist"].sudo()
        name = _("Lista pública %(currency)s", currency=currency.name)
        pl = Pricelist.search(
            [
                ("name", "=", name),
                ("currency_id", "=", currency.id),
                ("company_id", "in", [company.id, False]),
            ],
            limit=1,
        )
        if pl:
            return pl
        return Pricelist.create(
            {
                "name": name,
                "currency_id": currency.id,
                "company_id": company.id,
            }
        )

    def _sync_commercial_currency_defaults(self):
        """When commercial currency changes, align defaults and public lists."""
        for policy in self:
            if not policy.commercial_currency_id:
                continue
            updates = {}
            public_pl = policy._find_or_create_public_pricelist(
                policy.company_id, policy.commercial_currency_id
            )
            if not policy.default_pricelist_id or policy.default_pricelist_id.currency_id != policy.commercial_currency_id:
                updates["default_pricelist_id"] = public_pl.id
            if not policy.default_product_pricelist_id or policy.default_product_pricelist_id.currency_id != policy.commercial_currency_id:
                updates["default_product_pricelist_id"] = public_pl.id
            if policy.default_customer_currency_id != policy.commercial_currency_id:
                updates["default_customer_currency_id"] = policy.commercial_currency_id.id
            if updates:
                policy.write(updates)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_commercial_currency_defaults()
        return records

    def write(self, vals):
        if "commercial_currency_id" in vals:
            for policy in self:
                new_currency = self.env["res.currency"].browse(vals["commercial_currency_id"])
                public_pl = policy._find_or_create_public_pricelist(policy.company_id, new_currency)
                policy_vals = dict(vals)
                policy_vals.update(
                    {
                        "default_pricelist_id": public_pl.id,
                        "default_product_pricelist_id": public_pl.id,
                        "default_customer_currency_id": new_currency.id,
                    }
                )
                super(JustechMulticurrencyPolicy, policy).write(policy_vals)
            return True
        return super().write(vals)

    def action_open_dashboard(self):
        self.ensure_one()
        dashboard = self.env["justech.multicurrency.dashboard"].create(
            {"policy_id": self.id, "company_id": self.company_id.id}
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Dashboard Multimoneda"),
            "res_model": "justech.multicurrency.dashboard",
            "res_id": dashboard.id,
            "view_mode": "form",
            "target": "current",
        }
