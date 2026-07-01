"""Retenciones RD por factura en account.payment.register."""
from __future__ import annotations

from odoo import Command, api, fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    hellenia_withholding_line_ids = fields.One2many(
        "hellenia.payment.withholding.wizard.line",
        "register_wizard_id",
        string="Retenciones de la factura",
    )
    hellenia_withholding_total = fields.Monetary(
        compute="_compute_hellenia_withholding_total",
        string="Total retenido",
        currency_field="currency_id",
    )

    @api.depends("hellenia_withholding_line_ids.amount")
    def _compute_hellenia_withholding_total(self):
        for wiz in self:
            wiz.hellenia_withholding_total = sum(wiz.hellenia_withholding_line_ids.mapped("amount"))

    def _hellenia_invoice_for_batch(self, batch_result):
        move = self.env["account.move"]
        if batch_result and batch_result.get("lines"):
            move = batch_result["lines"].move_id[:1]
        if not move and self.line_ids:
            move = self.line_ids.move_id[:1]
        return move

    def _hellenia_persistent_vals(self, wh, default_move):
        move = default_move
        if getattr(wh, "wizard_line_id", False) and wh.wizard_line_id.move_id:
            move = wh.wizard_line_id.move_id
        return {
            "move_id": move.id if move else False,
            "invoice_name": move.name if move else "",
            "ncf": getattr(move, "justech_do_ncf", "") or "",
            "catalog_id": wh.catalog_id.id,
            "label": wh.label or (wh.catalog_id.name if wh.catalog_id else wh.tax_id.name),
            "base_label": wh.base_label,
            "base_amount": wh.base_amount,
            "rate": wh.rate,
            "amount": wh.amount,
            "account_id": wh.account_id.id,
        }

    def _hellenia_persistent_withholding_commands(self, batch_result):
        move = self._hellenia_invoice_for_batch(batch_result)
        commands = []
        for wh in self.hellenia_withholding_line_ids:
            if not wh.amount:
                continue
            commands.append(Command.create(self._hellenia_persistent_vals(wh, move)))
        return commands

    def _hellenia_apply_withholding_to_payment_vals(self, payment_vals, batch_result):
        """Inyecta retenciones en vals del pago usando el hook nativo de Odoo 19.

        No usa write_off_line_vals: las líneas contables se generan vía
        account.payment._prepare_move_withholding_lines() leyendo las líneas
        persistentes creadas junto al pago.
        """
        applied = self.amount or payment_vals.get("amount") or 0.0
        if applied:
            payment_vals["hellenia_applied_amount"] = applied

        wh_lines = self.hellenia_withholding_line_ids
        wh_total = sum(wh_lines.mapped("amount"))
        if not wh_total:
            return payment_vals

        payment_vals["hellenia_withholding_line_ids"] = self._hellenia_persistent_withholding_commands(
            batch_result
        )
        # Con _prepare_move_withholding_lines, Odoo resta la retención de la liquidez.
        # payment.amount debe ser el bruto aplicado; el banco queda en neto automáticamente.

        # Evitar doble contabilización: retención va por _prepare_move_withholding_lines.
        payment_vals["write_off_line_vals"] = []
        return payment_vals

    def _create_payment_vals_from_wizard(self, batch_result):
        vals = super()._create_payment_vals_from_wizard(batch_result)
        return self._hellenia_apply_withholding_to_payment_vals(vals, batch_result)

    def _create_payment_vals_from_batch(self, batch_result):
        vals = super()._create_payment_vals_from_batch(batch_result)
        return self._hellenia_apply_withholding_to_payment_vals(vals, batch_result)

    def _hellenia_finalize_persistent_lines(self, payment, batch_result):
        """Garantiza persistencia y vínculos contables post-create."""
        move = self._hellenia_invoice_for_batch(batch_result)
        WhLine = self.env["hellenia.payment.withholding.line"]
        AppLine = self.env["hellenia.payment.application.line"]
        for pay in payment:
            if not pay.hellenia_withholding_line_ids:
                for wh in self.hellenia_withholding_line_ids:
                    if not wh.amount:
                        continue
                    WhLine.create({"payment_id": pay.id, **self._hellenia_persistent_vals(wh, move)})
            if move and not pay.hellenia_application_line_ids:
                wh_lines = pay.hellenia_withholding_line_ids.filtered(lambda w: w.move_id == move)
                wh_amount = sum(wh_lines.mapped("amount"))
                applied = pay.hellenia_applied_amount or self.amount or pay.amount
                AppLine.create(
                    {
                        "payment_id": pay.id,
                        "move_id": move.id,
                        "invoice_name": move.name,
                        "ncf": getattr(move, "justech_do_ncf", "") or "",
                        "invoice_date": move.invoice_date,
                        "invoice_total": move.amount_total,
                        "applied_amount": applied,
                        "withholding_labels": ", ".join(filter(None, wh_lines.mapped("label"))),
                        "withholding_amount": wh_amount,
                        "net_amount": applied - wh_amount,
                        "reconciliation_state": "Pendiente",
                    }
                )
            pay._hellenia_link_withholding_move_lines()
            pay._hellenia_link_partial_reconciles()
            pay._hellenia_sync_application_lines()

    def _init_payments(self, to_process, edit_mode=False):
        payments = super()._init_payments(to_process, edit_mode=edit_mode)
        for payment, proc in zip(payments, to_process):
            self._hellenia_finalize_persistent_lines(payment, proc.get("batch"))
        return payments

    def _reconcile_payments(self, to_process, edit_mode=False):
        super()._reconcile_payments(to_process, edit_mode=edit_mode)
        payments = self.env["account.payment"].concat(*[p["payment"] for p in to_process])
        payments._hellenia_link_withholding_move_lines()
        payments._hellenia_link_partial_reconciles()
        payments._hellenia_sync_application_lines()
