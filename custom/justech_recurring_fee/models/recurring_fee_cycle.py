# -*- coding: utf-8 -*-
from odoo import fields, models


class JustechRecurringFeeCycle(models.Model):
    _name = "justech.recurring.fee.cycle"
    _description = "Ciclo generado de fee recurrente"
    _order = "cycle_number desc, id desc"
    _rec_name = "document_name"

    fee_id = fields.Many2one(
        "justech.recurring.fee",
        string="Fee",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one("res.company", required=True, index=True)
    period_key = fields.Char(string="Clave de período", required=True, index=True)
    period_from = fields.Date(string="Período desde", required=True)
    period_to = fields.Date(string="Período hasta", required=True)
    cycle_number = fields.Integer(string="Nº de ciclo", required=True)
    scheduled_date = fields.Date(string="Fecha programada")
    generated_at = fields.Datetime(string="Generado el")
    document_type = fields.Selection(
        [
            ("quotation_draft", "Cotización"),
            ("sale_order_draft", "Pedido de venta"),
            ("invoice_draft", "Factura borrador"),
            ("invoice_auto", "Factura publicada"),
        ],
        required=True,
    )
    sale_order_id = fields.Many2one("sale.order", string="Cotización / Pedido", index=True)
    invoice_id = fields.Many2one("account.move", string="Factura", index=True)
    document_name = fields.Char(string="Documento")
    state = fields.Selection(
        [("done", "Generado"), ("skipped", "Omitido (duplicado)"), ("error", "Error")],
        default="done",
    )
    note = fields.Text(string="Resultado")

    _period_key_uniq = models.Constraint(
        "unique(fee_id, period_key)",
        "Ya existe un documento para este fee, período y tipo.",
    )
