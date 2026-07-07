from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    justech_sale_price = fields.Float(
        string="Precio de venta comercial",
        digits="Product Price",
        help="Precio comercial definido por el vendedor, en la moneda seleccionada.",
    )
    justech_sale_currency_id = fields.Many2one(
        "res.currency",
        string="Moneda de venta",
        help="Moneda en la que el vendedor define el precio comercial.",
    )
    justech_purchase_price = fields.Float(
        string="Precio de compra comercial",
        digits="Product Price",
        help="Costo comercial definido en la moneda seleccionada.",
    )
    justech_purchase_currency_id = fields.Many2one(
        "res.currency",
        string="Moneda de compra",
        help="Moneda en la que se registra el costo comercial.",
    )
    justech_accounting_sale_price = fields.Float(
        string="Precio contable (auto)",
        compute="_compute_justech_accounting_prices",
        digits="Product Price",
        help="Equivalente en moneda de la empresa, sincronizado con list_price.",
    )
    justech_accounting_purchase_price = fields.Float(
        string="Costo contable (auto)",
        compute="_compute_justech_accounting_prices",
        digits="Product Price",
        help="Equivalente en moneda de la empresa, sincronizado con standard_price.",
    )
    justech_company_currency_id = fields.Many2one(
        "res.currency",
        string="Moneda contable empresa",
        compute="_compute_justech_commercial_display",
        help="Moneda funcional usada para el equivalente contable mostrado en pantalla.",
    )
    justech_sale_rate_used = fields.Float(
        string="Tasa venta",
        compute="_compute_justech_commercial_display",
        digits=(12, 4),
        help="Factor de conversión aplicado al precio de venta comercial.",
    )
    justech_purchase_rate_used = fields.Float(
        string="Tasa compra",
        compute="_compute_justech_commercial_display",
        digits=(12, 4),
        help="Factor de conversión aplicado al precio de compra comercial.",
    )
    justech_sale_rate_label = fields.Char(
        string="Tasa venta (texto)",
        compute="_compute_justech_commercial_display",
    )
    justech_purchase_rate_label = fields.Char(
        string="Tasa compra (texto)",
        compute="_compute_justech_commercial_display",
    )

    @api.depends("list_price", "standard_price")
    def _compute_justech_accounting_prices(self):
        for template in self:
            template.justech_accounting_sale_price = template.list_price
            template.justech_accounting_purchase_price = template.standard_price

    @api.depends(
        "justech_sale_price",
        "justech_sale_currency_id",
        "justech_purchase_price",
        "justech_purchase_currency_id",
        "company_id",
        "company_id.currency_id",
        "list_price",
        "standard_price",
    )
    def _compute_justech_commercial_display(self):
        Policy = self.env["justech.multicurrency.policy"]
        for template in self:
            company = template.company_id or self.env.company
            company_currency = company.currency_id
            template.justech_company_currency_id = company_currency

            sale_currency = template.justech_sale_currency_id or company_currency
            purchase_currency = template.justech_purchase_currency_id or company_currency

            template.justech_sale_rate_used = template._justech_display_rate(
                Policy, sale_currency, company
            )
            template.justech_purchase_rate_used = template._justech_display_rate(
                Policy, purchase_currency, company
            )
            template.justech_sale_rate_label = template._justech_format_rate_label(
                sale_currency, company_currency, template.justech_sale_rate_used
            )
            template.justech_purchase_rate_label = template._justech_format_rate_label(
                purchase_currency, company_currency, template.justech_purchase_rate_used
            )

    def _justech_display_rate(self, policy, currency, company):
        company_currency = company.currency_id
        if not currency or currency == company_currency:
            return 1.0
        return policy.convert_to_company_currency(1.0, currency, company=company, date=fields.Date.today())

    @staticmethod
    def _justech_format_rate_label(currency, company_currency, rate):
        if not currency or currency == company_currency:
            return f"Sin conversión ({company_currency.name})"
        return f"1 {currency.name} = {rate:,.2f} {company_currency.name}"

    @api.model
    def _justech_default_commercial_currency(self, company=None):
        company = company or self.env.company
        policy = self.env["justech.multicurrency.policy"].get_policy(company)
        return policy.commercial_currency_id or company.currency_id

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        for vals in vals_list:
            vals = dict(vals)
            company = self.env["res.company"].browse(vals.get("company_id")) if vals.get("company_id") else self.env.company
            default_currency = self._justech_default_commercial_currency(company)
            if not vals.get("justech_sale_currency_id") and default_currency:
                vals["justech_sale_currency_id"] = default_currency.id
            if not vals.get("justech_purchase_currency_id") and default_currency:
                vals["justech_purchase_currency_id"] = default_currency.id
            if vals.get("justech_sale_price") in (None, False) and vals.get("list_price") not in (None, False):
                vals["justech_sale_price"] = vals["list_price"]
            if vals.get("justech_purchase_price") in (None, False) and vals.get("standard_price") not in (None, False):
                vals["justech_purchase_price"] = vals["standard_price"]
            prepared.append(vals)
        templates = super().create(prepared)
        self.env.flush_all()
        if not self.env.context.get("justech_skip_commercial_sync"):
            templates._justech_sync_commercial_pricing()
            templates.invalidate_recordset(["list_price", "standard_price"])
        return templates

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get("justech_skip_commercial_sync"):
            return res
        sync_sale = bool({"justech_sale_price", "justech_sale_currency_id"} & set(vals))
        sync_purchase = bool({"justech_purchase_price", "justech_purchase_currency_id"} & set(vals))
        if sync_sale or sync_purchase:
            self.with_context(
                justech_sync_sale=sync_sale,
                justech_sync_purchase=sync_purchase,
            )._justech_sync_commercial_pricing()
        return res

    def _justech_sync_commercial_pricing(self):
        if self.env.context.get("justech_skip_commercial_sync"):
            return
        sync_sale = self.env.context.get("justech_sync_sale", True)
        sync_purchase = self.env.context.get("justech_sync_purchase", True)
        Policy = self.env["justech.multicurrency.policy"]
        Item = self.env["product.pricelist.item"].sudo()
        updates = {}
        for template in self:
            company = template.company_id or self.env.company
            company_currency = company.currency_id
            policy = Policy.get_policy(company)
            today = fields.Date.today()

            list_price = template.list_price
            standard_price = template.standard_price

            if sync_sale and template.justech_sale_price:
                sale_currency = template.justech_sale_currency_id or policy.commercial_currency_id or company_currency
                list_price = Policy.convert_to_company_currency(
                    template.justech_sale_price or 0.0,
                    sale_currency,
                    company=company,
                    date=today,
                )
                if sale_currency and template.justech_sale_price:
                    sale_pl = policy._find_or_create_public_pricelist(company, sale_currency)
                    template._justech_upsert_pricelist_item(Item, sale_pl, template.justech_sale_price)

            if sync_purchase and template.justech_purchase_price:
                purchase_currency = (
                    template.justech_purchase_currency_id or company_currency
                )
                standard_price = Policy.convert_to_company_currency(
                    template.justech_purchase_price or 0.0,
                    purchase_currency,
                    company=company,
                    date=today,
                )

            updates[template.id] = {}
            if sync_sale:
                updates[template.id]["list_price"] = list_price
            if sync_purchase:
                updates[template.id]["standard_price"] = standard_price

        for template in self:
            payload = updates.get(template.id) or {}
            if not payload:
                continue
            super(ProductTemplate, template.with_context(justech_skip_commercial_sync=True)).write(payload)

    def _justech_upsert_pricelist_item(self, Item, pricelist, price, compute_price="fixed"):
        self.ensure_one()
        item = Item.search(
            [
                ("pricelist_id", "=", pricelist.id),
                ("product_tmpl_id", "=", self.id),
                ("applied_on", "=", "1_product"),
            ],
            limit=1,
        )
        vals = {
            "pricelist_id": pricelist.id,
            "applied_on": "1_product",
            "product_tmpl_id": self.id,
            "compute_price": compute_price,
            "fixed_price": price,
        }
        ctx = {"justech_skip_audit": True, "tracking_disable": True, "justech_skip_commercial_sync": True}
        if item:
            item.with_context(**ctx).write({"compute_price": "fixed", "fixed_price": price})
        else:
            Item.with_context(**ctx).create(vals)

    @api.model
    def _justech_resync_for_currency(self, currency):
        if not currency:
            return
        templates = self.search(
            [
                "|",
                ("justech_sale_currency_id", "=", currency.id),
                ("justech_purchase_currency_id", "=", currency.id),
            ]
        )
        if templates:
            templates.with_context(
                justech_sync_sale=True,
                justech_sync_purchase=True,
            )._justech_sync_commercial_pricing()
