from odoo import api, fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    hellenia_invoice_summary = fields.Text(
        string="Facturas seleccionadas",
        compute="_compute_hellenia_invoice_summary",
    )

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
