# -*- coding: utf-8 -*-
"""Redirige el botón nativo de factura al wizard único Justech."""
from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_register_payment(self):
        """Único camino operativo: justech.payment.partner.wizard.

        El wizard nativo account.payment.register sigue existiendo para uso
        interno del wizard Justech; no se abre desde la factura.
        """
        self.ensure_one()
        if (
            self.state != "posted"
            or self.payment_state in ("paid", "reversed", "invoicing_legacy")
            or self.currency_id.is_zero(self.amount_residual)
        ):
            return super().action_register_payment()

        partner_type = "customer" if self.is_sale_document(include_receipts=True) else "supplier"
        action_xmlid = (
            "justech_l10n_do_payments_withholding.action_justech_register_customer_payment"
            if partner_type == "customer"
            else "justech_l10n_do_payments_withholding.action_justech_register_vendor_payment"
        )
        action = self.env["ir.actions.act_window"]._for_xml_id(action_xmlid)
        ctx = dict(self.env.context)
        ctx.update(
            {
                "default_partner_type": partner_type,
                "default_partner_id": self.partner_id.id,
                "default_currency_id": self.currency_id.id,
                "active_model": "account.move",
                "active_ids": self.ids,
                "active_id": self.id,
                "justech_preselect_move_ids": self.ids,
            }
        )
        action["context"] = ctx
        return action
