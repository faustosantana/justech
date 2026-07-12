from odoo import fields, models


class JustechEcfDocumentEvent(models.Model):
    _name = "justech.ecf.document.event"
    _description = "Evento de trazabilidad e-CF"
    _order = "id desc"

    document_id = fields.Many2one("justech.ecf.document", required=True, index=True, ondelete="cascade")
    company_id = fields.Many2one("res.company", required=True, index=True)
    event_type = fields.Char(required=True, index=True)
    result = fields.Selection(
        selection=[("ok", "OK"), ("error", "Error"), ("warn", "Advertencia")],
        default="ok",
        required=True,
    )
    message = fields.Text()
    payload = fields.Text()
    duration_ms = fields.Integer()
    attempt = fields.Integer()
    user_id = fields.Many2one("res.users")
    create_date = fields.Datetime(readonly=True)
