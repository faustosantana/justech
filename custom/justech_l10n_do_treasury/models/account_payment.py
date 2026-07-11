"""Campos de visualización para Pagos abiertos (sin alterar lógica contable)."""
from __future__ import annotations

from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    treasury_amount_applied = fields.Monetary(
        string="Aplicado (pago abierto)",
        currency_field="currency_id",
        compute="_compute_treasury_open_metrics",
        store=True,
    )
    treasury_amount_available = fields.Monetary(
        string="Saldo disponible",
        currency_field="currency_id",
        compute="_compute_treasury_open_metrics",
        store=True,
    )
    treasury_open_state = fields.Selection(
        [
            ("open", "Abierto"),
            ("partial", "Aplicado parcialmente"),
            ("applied", "Aplicado completamente"),
            ("cancelled", "Anulado"),
        ],
        string="Estado pago abierto",
        compute="_compute_treasury_open_metrics",
        store=True,
    )
    treasury_is_open = fields.Boolean(
        string="Es pago abierto",
        compute="_compute_treasury_open_metrics",
        store=True,
        index=True,
    )
    treasury_concept = fields.Char(
        string="Concepto",
        compute="_compute_treasury_concept",
    )
    treasury_bank_state = fields.Selection(
        [
            ("not_posted", "No requiere conciliación"),
            ("bank_pending", "Pendiente de conciliación"),
            ("bank_reconciled", "Conciliado"),
        ],
        string="Estado bancario",
        compute="_compute_treasury_bank_state",
        store=True,
    )
    treasury_payment_reference = fields.Char(
        string="Referencia",
        related="justech_payment_reference",
        readonly=True,
    )

    @api.model
    def _treasury_counterpart_lines(self, payment):
        if not payment.move_id:
            return payment.env["account.move.line"]
        valid_types = payment._get_valid_payment_account_types()
        return payment.move_id.line_ids.filtered(
            lambda line: line.account_id.account_type in valid_types
        )

    @api.model
    def _treasury_available_amount(self, payment):
        lines = self._treasury_counterpart_lines(payment)
        if not lines:
            return 0.0
        return sum(abs(line.amount_residual) for line in lines)

    @api.model
    def _treasury_search_open_for_partner(self, partner, partner_type):
        payment_type = "inbound" if partner_type == "customer" else "outbound"
        candidates = self.search(
            [
                ("partner_id", "=", partner.id),
                ("partner_type", "=", partner_type),
                ("payment_type", "=", payment_type),
                ("treasury_is_open", "=", True),
            ]
        )
        return candidates

    @api.depends("memo", "payment_reference", "name")
    def _compute_treasury_concept(self):
        """Concepto de pago — solo campos reales de account.payment en Odoo 19.

        Odoo 19 no tiene ``ref`` en account.payment; la fuente principal es ``memo``.
        """
        for pay in self:
            concept = ""
            if "memo" in pay._fields:
                concept = (pay.memo or "").strip()
            if not concept and "payment_reference" in pay._fields:
                concept = (pay.payment_reference or "").strip()
            if not concept and "name" in pay._fields:
                concept = (pay.name or "").strip()
            pay.treasury_concept = concept

    @api.depends(
        "state",
        "outstanding_account_id",
        "move_id.line_ids.reconciled",
        "move_id.line_ids.account_id",
        "move_id.line_ids.account_id.account_type",
    )
    def _compute_treasury_bank_state(self):
        """Estado bancario vs conciliación de liquidez / outstanding.

        Con cuentas outstanding (estándar Odoo), la partida a conciliar con el
        extracto suele ser ``asset_current`` (u otro tipo), no ``asset_cash``.
        Antes solo se miraba cash/credit_card → ``bank_pending`` falso tras conciliar.
        """
        liquidity_types = ("asset_cash", "asset_credit_card")
        for pay in self:
            if pay.state not in ("in_process", "paid"):
                pay.treasury_bank_state = "not_posted"
                continue
            if not pay.move_id:
                pay.treasury_bank_state = "bank_pending"
                continue
            liquidity_lines = pay.move_id.line_ids.filtered(
                lambda line: line.account_id.account_type in liquidity_types
            )
            if pay.outstanding_account_id:
                outstanding_lines = pay.move_id.line_ids.filtered(
                    lambda line: line.account_id == pay.outstanding_account_id
                )
                if outstanding_lines:
                    liquidity_lines = outstanding_lines
            if not liquidity_lines:
                pay.treasury_bank_state = "bank_pending"
            elif all(line.reconciled for line in liquidity_lines):
                pay.treasury_bank_state = "bank_reconciled"
            else:
                pay.treasury_bank_state = "bank_pending"

    @api.depends(
        "state",
        "amount",
        "currency_id",
        "move_id.line_ids.amount_residual",
        "move_id.line_ids.matched_debit_ids",
        "move_id.line_ids.matched_credit_ids",
    )
    def _compute_treasury_open_metrics(self):
        for pay in self:
            rounding = pay.currency_id.rounding or 0.01
            if pay.state == "canceled":
                pay.treasury_open_state = "cancelled"
                pay.treasury_amount_applied = 0.0
                pay.treasury_amount_available = 0.0
                pay.treasury_is_open = False
                continue

            if pay.state not in ("in_process", "paid"):
                pay.treasury_open_state = "open"
                pay.treasury_amount_applied = 0.0
                pay.treasury_amount_available = 0.0
                pay.treasury_is_open = False
                continue

            available = self._treasury_available_amount(pay)
            applied = max(pay.amount - available, 0.0)
            pay.treasury_amount_available = available
            pay.treasury_amount_applied = applied

            if available <= rounding:
                pay.treasury_open_state = "applied" if applied > rounding else "applied"
                pay.treasury_is_open = False
            elif applied <= rounding:
                pay.treasury_open_state = "open"
                pay.treasury_is_open = True
            else:
                pay.treasury_open_state = "partial"
                pay.treasury_is_open = True

    def action_treasury_apply_to_invoice(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Aplicar pago abierto",
            "res_model": "treasury.open.payment.apply.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_payment_id": self.id,
                "default_partner_id": self.partner_id.id,
                "default_partner_type": self.partner_type,
            },
        }

    def action_treasury_view_move(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Asiento contable",
            "res_model": "account.move",
            "res_id": self.move_id.id,
            "view_mode": "form",
        }

    def action_treasury_view_reconciliation(self):
        self.ensure_one()
        lines = self._treasury_counterpart_lines(self)
        return {
            "type": "ir.actions.act_window",
            "name": "Conciliación",
            "res_model": "account.move.line",
            "view_mode": "list,form",
            "domain": [("id", "in", lines.ids)],
        }
