"""Trazabilidad retención 5% Gobierno en pagos — alimenta formato 623."""
from odoo import fields, models

GOV_CATALOG_CODES = ("RET-GOB-5", "wh_isr_gov")


class AccountPaymentGov623(models.Model):
    _inherit = "account.payment"

    justech_do_gov_withholding_amount = fields.Float(
        string="Retención 5% Gobierno",
        digits=(16, 2),
        copy=False,
        help="Monto retenido por entidad del Estado en este pago.",
    )
    justech_do_gov_withholding_catalog_id = fields.Many2one(
        "hellenia.withholding.catalog",
        string="Catálogo retención Gobierno",
        copy=False,
    )

    def _justech_stamp_gov_from_withholding(self):
        """Stamp campos 623 en pago y facturas conciliadas."""
        for pay in self:
            gov_lines = pay.hellenia_withholding_line_ids.filtered(
                lambda w: w.catalog_id.code in GOV_CATALOG_CODES and w.amount
            )
            if not gov_lines:
                continue
            amount = sum(gov_lines.mapped("amount"))
            ref = pay.hellenia_check_number or pay.hellenia_payment_reference or pay.name or ""
            ref_type = "1" if pay.hellenia_check_number else "2"
            pay.write(
                {
                    "justech_do_gov_withholding_amount": amount,
                    "justech_do_gov_withholding_catalog_id": gov_lines[:1].catalog_id.id,
                }
            )
            move_vals = {
                "justech_do_gov_withholding_amount": amount,
                "justech_do_gov_retention_date": pay.date,
                "justech_do_gov_retention_ref": ref,
                "justech_do_gov_retention_ref_type": ref_type,
            }
            if pay.hellenia_check_bank_id:
                move_vals["justech_do_gov_retention_bank_id"] = pay.hellenia_check_bank_id.id
            moves = pay.reconciled_invoice_ids | pay.reconciled_bill_ids
            if not moves:
                moves = gov_lines.mapped("move_id")
            if moves:
                moves.write(move_vals)


class AccountPaymentRegisterGov623(models.TransientModel):
    _inherit = "account.payment.register"

    def _justech_gov_withholding_payload(self):
        self.ensure_one()
        lines = self.hellenia_withholding_line_ids.filtered(
            lambda w: w.catalog_id.code in GOV_CATALOG_CODES and w.amount
        )
        if not lines:
            return {}, {}
        amount = sum(lines.mapped("amount"))
        catalog = lines[0].catalog_id
        ref_type = "1" if self.hellenia_check_number else "2"
        ref = self.hellenia_check_number or self.hellenia_payment_reference or ""
        payment_vals = {
            "justech_do_gov_withholding_amount": amount,
            "justech_do_gov_withholding_catalog_id": catalog.id,
        }
        move_vals = {
            "justech_do_gov_withholding_amount": amount,
            "justech_do_gov_retention_date": self.payment_date,
            "justech_do_gov_retention_ref": ref,
            "justech_do_gov_retention_ref_type": ref_type,
            "justech_do_gov_retention_bank_id": self.hellenia_check_bank_id.id,
        }
        return payment_vals, move_vals

    def _create_payment_vals_from_wizard(self, batch_result):
        vals = super()._create_payment_vals_from_wizard(batch_result)
        payment_vals, _move_vals = self._justech_gov_withholding_payload()
        if payment_vals:
            vals.update(payment_vals)
        return vals

    def _hellenia_stamp_gov_on_invoices(self, payments):
        payments._justech_stamp_gov_from_withholding()
        super()._hellenia_stamp_gov_on_invoices(payments)
