from odoo import api, fields, models, tools
from odoo.exceptions import AccessError, ValidationError


class JustechAuditLog(models.Model):
    _name = "justech.audit.log"
    _description = "Justech Global Audit Log"
    _order = "change_date desc, id desc"
    _rec_name = "record_name"

    operation_type = fields.Selection(
        selection=[
            ("create", "Creación"),
            ("write", "Modificación"),
            ("unlink", "Eliminación"),
            ("event", "Evento"),
        ],
        required=True,
        index=True,
    )
    model_name = fields.Char(required=True, index=True)
    model_description = fields.Char(string="Modelo", index=True)
    record_id = fields.Integer(required=True, index=True)
    record_name = fields.Char(index=True)
    field_name = fields.Char(string="Campo técnico", index=True)
    field_description = fields.Char(string="Campo", index=True)
    old_value = fields.Text(string="Valor anterior")
    new_value = fields.Text(string="Valor nuevo")
    user_id = fields.Many2one("res.users", string="Usuario", index=True, ondelete="set null")
    company_id = fields.Many2one("res.company", string="Empresa", index=True, ondelete="set null")
    change_date = fields.Datetime(
        string="Fecha de cambio",
        default=fields.Datetime.now,
        required=True,
        index=True,
    )
    ip_address = fields.Char(string="Dirección IP", index=True)
    event_source = fields.Char(string="Origen evento", index=True)
    correlation_id = fields.Char(string="Correlation ID", index=True)

    def init(self):
        super().init()
        cr = self.env.cr
        tools.create_index(
            cr,
            "justech_audit_log_model_record_date_idx",
            self._table,
            ["model_name", "record_id", "change_date"],
        )
        tools.create_index(
            cr,
            "justech_audit_log_company_date_idx",
            self._table,
            ["company_id", "change_date"],
        )
        tools.create_index(
            cr,
            "justech_audit_log_user_date_idx",
            self._table,
            ["user_id", "change_date"],
        )

    def write(self, vals):
        if self.env.context.get("justech_internal_log"):
            return super().write(vals)
        raise AccessError("Los registros de auditoría son inmutables.")

    def unlink(self):
        if self.env.context.get("justech_retention_purge"):
            return super().unlink()
        raise AccessError("Los registros de auditoría no pueden eliminarse manualmente.")

    @api.model
    def _purge_before(self, cutoff_date, batch_size=5000):
        total = 0
        while True:
            records = self.with_context(justech_retention_purge=True).search(
                [("change_date", "<", cutoff_date)],
                limit=batch_size,
                order="id",
            )
            if not records:
                break
            count = len(records)
            records.unlink()
            total += count
            if count < batch_size:
                break
        return total
