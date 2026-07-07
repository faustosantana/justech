from odoo import api, fields, models


class JustechAuditDashboard(models.TransientModel):
    _name = "justech.audit.dashboard"
    _description = "Justech Audit Dashboard"

    total_logs = fields.Integer(compute="_compute_stats")
    logs_today = fields.Integer(compute="_compute_stats")
    logs_week = fields.Integer(compute="_compute_stats")
    active_rules = fields.Integer(compute="_compute_stats")
    active_policies = fields.Integer(compute="_compute_stats")
    top_model_name = fields.Char(compute="_compute_stats", string="Modelo más auditado")
    top_model_count = fields.Integer(compute="_compute_stats")
    last_retention_run = fields.Datetime(compute="_compute_stats")
    last_purged_count = fields.Integer(compute="_compute_stats")

    @api.depends_context("uid")
    def _compute_stats(self):
        Log = self.env["justech.audit.log"].sudo()
        today = fields.Date.context_today(self)
        week_start = fields.Date.subtract(today, days=7)
        for dashboard in self:
            dashboard.total_logs = Log.search_count([])
            dashboard.logs_today = Log.search_count(
                [("change_date", ">=", fields.Datetime.to_datetime(today))]
            )
            dashboard.logs_week = Log.search_count(
                [("change_date", ">=", fields.Datetime.to_datetime(week_start))]
            )
            dashboard.active_rules = self.env["justech.audit.rule"].search_count(
                [("active", "=", True)]
            )
            dashboard.active_policies = self.env["justech.audit.policy"].search_count(
                [("active", "=", True)]
            )
            groups = Log.read_group(
                [],
                ["model_name"],
                ["model_name"],
                orderby="model_name_count desc",
                limit=1,
            )
            if groups:
                dashboard.top_model_name = groups[0]["model_name"]
                dashboard.top_model_count = groups[0].get("model_name_count") or groups[0].get(
                    "__count", 0
                )
            else:
                dashboard.top_model_name = False
                dashboard.top_model_count = 0
            retention = self.env["justech.audit.retention"].search(
                [("active", "=", True)], limit=1
            )
            dashboard.last_retention_run = retention.last_run_at if retention else False
            dashboard.last_purged_count = retention.last_purged_count if retention else 0

    def action_open_logs(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Logs de auditoría",
            "res_model": "justech.audit.log",
            "view_mode": "list,form",
        }

    def action_open_rules(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Reglas de auditoría",
            "res_model": "justech.audit.rule",
            "view_mode": "list,form",
            "context": {"search_default_filter_active": 1},
        }

    def action_export_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Exportar auditoría",
            "res_model": "justech.audit.export.wizard",
            "view_mode": "form",
            "target": "new",
        }
