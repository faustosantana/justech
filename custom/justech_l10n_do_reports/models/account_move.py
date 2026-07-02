"""Campos configurables DGII 609 — pagos al exterior."""
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    justech_do_foreign_609 = fields.Boolean(
        string="Reportar en 609",
        copy=False,
        help="Incluir este documento en el formato 609 aunque el proveedor no tenga país extranjero.",
    )
    justech_do_foreign_service_type = fields.Selection(
        selection=[
            ("01", "Alquileres"),
            ("02", "Honorarios por servicios técnicos"),
            ("03", "Regalías"),
            ("04", "Dividendos"),
            ("05", "Intereses"),
            ("06", "Servicios de transporte"),
            ("07", "Publicidad"),
            ("08", "Telecomunicaciones"),
            ("09", "Otros servicios"),
        ],
        string="Tipo servicio exterior (609)",
        copy=False,
    )
    justech_do_foreign_document_ref = fields.Char(
        string="Documento exterior (609)",
        copy=False,
        help="Número de factura, contrato o recibo que sustenta el pago al exterior.",
    )
    justech_do_foreign_payment_date = fields.Date(
        string="Fecha pago/retención exterior (609)",
        copy=False,
    )
    justech_do_foreign_exchange_rate = fields.Float(
        string="Tasa de cambio (609)",
        digits=(16, 6),
        copy=False,
    )
    justech_do_foreign_presumed_income = fields.Float(
        string="Renta presunta (609)",
        digits=(16, 2),
        copy=False,
    )
    justech_do_foreign_isr_retained = fields.Float(
        string="ISR retenido exterior (609)",
        digits=(16, 2),
        copy=False,
    )
