from odoo import api, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        partners._justech_apply_multicurrency_defaults(vals_list)
        return partners

    def _justech_apply_multicurrency_defaults(self, vals_list=None):
        if self.env.context.get("justech_skip_multicurrency_defaults"):
            return
        Policy = self.env["justech.multicurrency.policy"]
        for partner, vals in zip(self, vals_list or [{}] * len(self)):
            company = partner.company_id or self.env.company
            policy = Policy.get_policy(company)
            is_customer = bool(vals.get("customer_rank", partner.customer_rank))
            is_supplier = bool(vals.get("supplier_rank", partner.supplier_rank))
            if is_customer and policy.default_pricelist_id:
                partner.with_company(company).property_product_pricelist = policy.default_pricelist_id
            if is_supplier and policy.default_supplier_currency_id and "property_purchase_currency_id" in partner._fields:
                partner.with_company(company).property_purchase_currency_id = (
                    policy.default_supplier_currency_id
                )
