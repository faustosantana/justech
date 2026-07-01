from odoo import api, fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    hellenia_invoice_summary = fields.Text(
        string="Facturas seleccionadas",
        compute="_compute_hellenia_invoice_summary",
    )
    hellenia_payment_reference = fields.Char(string="Referencia")
    hellenia_card_auth = fields.Char(string="Autorización")
    hellenia_card_batch = fields.Char(string="Lote")
    hellenia_check_number = fields.Char(string="Número de cheque")
    hellenia_check_bank_id = fields.Many2one("res.bank", string="Banco del cheque")
    hellenia_check_date = fields.Date(string="Fecha del cheque")
    hellenia_show_card_fields = fields.Boolean(compute="_compute_hellenia_method_flags")
    hellenia_show_check_fields = fields.Boolean(compute="_compute_hellenia_method_flags")

    @api.depends("payment_method_line_id.name")
    def _compute_hellenia_method_flags(self):
        for wiz in self:
            name = (wiz.payment_method_line_id.name or "").lower()
            wiz.hellenia_show_card_fields = "tarjeta" in name
            wiz.hellenia_show_check_fields = "cheque" in name

    def _hellenia_extra_payment_vals(self):
        self.ensure_one()
        vals = {
            "hellenia_payment_reference": self.hellenia_payment_reference,
            "hellenia_card_auth": self.hellenia_card_auth,
            "hellenia_card_batch": self.hellenia_card_batch,
            "hellenia_check_number": self.hellenia_check_number,
            "hellenia_check_bank_id": self.hellenia_check_bank_id.id,
            "hellenia_check_date": self.hellenia_check_date,
        }
        if self.hellenia_payment_reference:
            vals["memo"] = self.hellenia_payment_reference
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        """Preserva monto parcial del partner wizard — Odoo _compute_amount resetea sin custom_user_amount."""
        prepared = []
        for vals in vals_list:
            vals = dict(vals)
            forced = vals.get("custom_user_amount") or self.env.context.get("hellenia_applied_amount")
            if forced is not None:
                vals["amount"] = forced
                vals["custom_user_amount"] = forced
                if not vals.get("custom_user_currency_id"):
                    vals["custom_user_currency_id"] = vals.get("currency_id")
                vals.setdefault("payment_difference_handling", "open")
            prepared.append(vals)
        registers = super().create(prepared)
        for register, vals in zip(registers, prepared):
            forced = vals.get("custom_user_amount")
            if forced is None:
                continue
            if register.currency_id.compare_amounts(register.amount, forced) != 0:
                register.write(
                    {
                        "amount": forced,
                        "custom_user_amount": forced,
                        "custom_user_currency_id": register.currency_id.id,
                        "payment_difference_handling": "open",
                    }
                )
        return registers

    def _create_payment_vals_from_wizard(self, batch_result):
        vals = super()._create_payment_vals_from_wizard(batch_result)
        vals.update(self._hellenia_extra_payment_vals())
        return vals

    def _create_payment_vals_from_batch(self, batch_result):
        vals = super()._create_payment_vals_from_batch(batch_result)
        vals.update(self._hellenia_extra_payment_vals())
        return vals

    @api.depends("line_ids")
    def _compute_hellenia_invoice_summary(self):
        for wizard in self:
            lines = []
            for line in wizard.line_ids:
                move = line.move_id
                ncf = getattr(move, "justech_do_ncf", False) or ""
                lines.append(
                    f"{move.name} | NCF: {ncf or '—'} | Vence: {line.date_maturity or '—'} | "
                    f"Residual: {line.amount_residual:.2f} {line.currency_id.name}"
                )
            wizard.hellenia_invoice_summary = "\n".join(lines) if lines else False
