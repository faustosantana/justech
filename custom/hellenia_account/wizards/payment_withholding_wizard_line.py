"""Línea transitoria de retención — wizard de pagos."""
from __future__ import annotations

from odoo import fields, models


class HelleniaPaymentWithholdingWizardLine(models.TransientModel):
    _name = "hellenia.payment.withholding.wizard.line"
    _description = "Detalle retención transitorio — wizard pago"

    wizard_id = fields.Many2one("hellenia.payment.partner.wizard", ondelete="cascade")
    wizard_line_id = fields.Many2one("hellenia.payment.partner.wizard.line", ondelete="cascade")
    register_wizard_id = fields.Many2one("account.payment.register", ondelete="cascade")
    catalog_id = fields.Many2one("hellenia.withholding.catalog", string="Retención")
    tax_id = fields.Many2one("account.tax", string="Impuesto")
    label = fields.Char(string="Descripción")
    base_label = fields.Char(string="Tipo de base")
    base_amount = fields.Monetary(string="Base", currency_field="currency_id")
    rate = fields.Float(string="Porcentaje")
    amount = fields.Monetary(string="Monto retenido", currency_field="currency_id")
    account_id = fields.Many2one("account.account", string="Cuenta contable")
    currency_id = fields.Many2one("res.currency", string="Moneda")
    invoice_name = fields.Char(related="wizard_line_id.invoice_name", string="Factura")
