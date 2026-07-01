"""Retenciones RD por factura en account.payment.register — flujo nativo Odoo 19."""
from __future__ import annotations

from odoo import Command, api, fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    hellenia_withholding_catalog_ids = fields.Many2many(
        "hellenia.withholding.catalog",
        "hellenia_payment_register_wh_catalog_rel",
        "register_id",
        "catalog_id",
        string="Retenciones",
        help="Seleccione retenciones a aplicar en este cobro/pago.",
    )
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

    def _hellenia_partner_type(self):
        self.ensure_one()
        if self.payment_type == "inbound":
            return "customer"
        if self.payment_type == "outbound":
            return "supplier"
        return "customer"

    def _hellenia_invoice_for_batch(self, batch_result):
        move = self.env["account.move"]
        if batch_result and batch_result.get("lines"):
            move = batch_result["lines"].move_id[:1]
        if not move and self.line_ids:
            move = self.line_ids.move_id[:1]
        return move

    def _hellenia_rebuild_register_withholding_lines(self):
        Catalog = self.env["hellenia.withholding.catalog"]
        for wiz in self:
            move = wiz._hellenia_invoice_for_batch({})
            if not move:
                wiz.hellenia_withholding_line_ids = [Command.clear()]
                continue
            partner_type = wiz._hellenia_partner_type()
            applied = wiz.custom_user_amount or wiz.amount or abs(move.amount_residual)
            details = [Command.clear()]
            for catalog in wiz.hellenia_withholding_catalog_ids:
                if not catalog._applies_to_move(move, partner_type):
                    continue
                amount = catalog.compute_withholding_amount(move, applied_amount=applied)
                if not amount or not catalog.account_id:
                    continue
                details.append(
                    Command.create(
                        {
                            "catalog_id": catalog.id,
                            "tax_id": catalog.tax_id.id,
                            "label": catalog.name,
                            "base_label": catalog._base_label(),
                            "base_amount": catalog._base_amount(move, applied_amount=applied),
                            "rate": catalog.rate,
                            "amount": amount,
                            "account_id": catalog.account_id.id,
                            "currency_id": wiz.currency_id.id,
                        }
                    )
                )
            wiz.hellenia_withholding_line_ids = details

    @api.onchange("hellenia_withholding_catalog_ids", "amount")
    def _onchange_hellenia_withholding_catalogs(self):
        self._hellenia_rebuild_register_withholding_lines()

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
            if not wh.amount or not wh.account_id:
                continue
            commands.append(Command.create(self._hellenia_persistent_vals(wh, move)))
        return commands

    def _hellenia_apply_withholding_to_payment_vals(self, payment_vals, batch_result):
        """Retenciones vía hook nativo _prepare_move_withholding_lines."""
        applied = self.custom_user_amount or self.amount or payment_vals.get("amount") or 0.0
        if applied:
            payment_vals["hellenia_applied_amount"] = applied

        wh_lines = self.hellenia_withholding_line_ids.filtered("amount")
        wh_total = sum(wh_lines.mapped("amount"))
        if not wh_total:
            return payment_vals

        payment_vals["hellenia_withholding_line_ids"] = self._hellenia_persistent_withholding_commands(
            batch_result
        )
        # payment.amount = bruto; banco = neto vía hook nativo.
        if wh_total:
            payment_vals["write_off_line_vals"] = []
        return payment_vals

    def _create_payment_vals_from_wizard(self, batch_result):
        if self.hellenia_withholding_catalog_ids:
            self._hellenia_rebuild_register_withholding_lines()
        vals = super()._create_payment_vals_from_wizard(batch_result)
        return self._hellenia_apply_withholding_to_payment_vals(vals, batch_result)

    def _create_payment_vals_from_batch(self, batch_result):
        vals = super()._create_payment_vals_from_batch(batch_result)
        return self._hellenia_apply_withholding_to_payment_vals(vals, batch_result)

    def _hellenia_ensure_move_withholding_lines(self, payment):
        """Re-sincroniza asiento si las líneas persistentes no generaron GL."""
        payment.ensure_one()
        if payment.state != "draft" or not payment.hellenia_withholding_line_ids:
            return
        wh_accounts = payment.hellenia_withholding_line_ids.mapped("account_id")
        gl_wh = payment.move_id.line_ids.filtered(lambda l: l.account_id in wh_accounts)
        if not gl_wh:
            payment._synchronize_to_moves(set())

    def _hellenia_finalize_persistent_lines(self, payment, batch_result):
        """Persistencia, vínculos contables y stamp fiscal post-create."""
        move = self._hellenia_invoice_for_batch(batch_result)
        WhLine = self.env["hellenia.payment.withholding.line"]
        AppLine = self.env["hellenia.payment.application.line"]
        for pay in payment:
            if not pay.hellenia_withholding_line_ids:
                for wh in self.hellenia_withholding_line_ids:
                    if not wh.amount or not wh.account_id:
                        continue
                    WhLine.create({"payment_id": pay.id, **self._hellenia_persistent_vals(wh, move)})
            self._hellenia_ensure_move_withholding_lines(pay)
            pay._hellenia_refresh_stored_totals()
            if move and not pay.hellenia_application_line_ids:
                wh_lines = pay.hellenia_withholding_line_ids.filtered(lambda w: w.move_id == move)
                wh_amount = sum(wh_lines.mapped("amount"))
                applied = pay.hellenia_applied_amount or self.custom_user_amount or self.amount or pay.amount
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

    def _init_payments(self, to_process, edit_mode=False):
        payments = super()._init_payments(to_process, edit_mode=edit_mode)
        for payment, proc in zip(payments, to_process):
            self._hellenia_finalize_persistent_lines(payment, proc.get("batch"))
        return payments

    def _hellenia_stamp_gov_on_invoices(self, payments):
        """Delegado a extensión fiscal si está instalada."""
        stamp = getattr(payments, "_justech_stamp_gov_from_withholding", None)
        if stamp:
            stamp()

    def _reconcile_payments(self, to_process, edit_mode=False):
        super()._reconcile_payments(to_process, edit_mode=edit_mode)
        payments = self.env["account.payment"].concat(*[p["payment"] for p in to_process])
        payments._hellenia_link_withholding_move_lines()
        payments._hellenia_link_partial_reconciles()
        payments._hellenia_sync_application_lines()
        payments._hellenia_refresh_stored_totals()
        self._hellenia_stamp_gov_on_invoices(payments)
