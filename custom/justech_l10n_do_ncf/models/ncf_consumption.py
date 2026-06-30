from odoo import fields, models


class JustechDoNcfConsumption(models.Model):
    _name = "justech.do.ncf.consumption"
    _description = "NCF Consumption Audit"
    _order = "consumption_date desc, id desc"

    range_id = fields.Many2one(
        "justech.do.ncf.range",
        required=True,
        ondelete="restrict",
    )
    move_id = fields.Many2one("account.move", ondelete="set null")
    ncf = fields.Char(required=True, index=True)
    sequence_number = fields.Integer()
    consumption_date = fields.Datetime(
        default=fields.Datetime.now,
        required=True,
    )
    state = fields.Selection(
        selection=[
            ("consumed", "Consumed"),
            ("voided", "Voided"),
        ],
        default="consumed",
        required=True,
    )
    company_id = fields.Many2one(
        related="range_id.company_id",
        store=True,
    )
