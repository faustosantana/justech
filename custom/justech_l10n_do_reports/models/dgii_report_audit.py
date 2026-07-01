# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class JustechDoDgiiReportAudit(models.Model):
    _name = "justech.do.dgii.report.audit"
    _description = "Bitácora auditoría reporte DGII"
    _order = "create_date desc, id desc"

    report_id = fields.Many2one(
        "justech.do.fiscal.report",
        string="Reporte",
        required=True,
        ondelete="cascade",
        index=True,
    )
    event_type = fields.Selection(
        selection=[
            ("create", "Creación revisión"),
            ("validate", "Validación"),
            ("exclude", "Exclusión"),
            ("include", "Re-inclusión"),
            ("submit_approval", "Envío a aprobación"),
            ("approve", "Aprobación"),
            ("reject", "Rechazo"),
            ("correction", "Corrección solicitada"),
            ("generate", "Generación Excel"),
            ("reopen", "Reapertura"),
            ("state_change", "Cambio de estado"),
        ],
        string="Evento",
        required=True,
    )
    user_id = fields.Many2one("res.users", string="Usuario", required=True)
    move_id = fields.Many2one("account.move", string="Documento")
    line_id = fields.Many2one("justech.do.fiscal.report.line", string="Línea reporte")
    description = fields.Text(string="Detalle")
    file_hash = fields.Char(string="Hash archivo")
    file_name = fields.Char(string="Nombre archivo")
    can_decide = fields.Boolean(compute="_compute_can_decide")
    permission_hint = fields.Char(compute="_compute_can_decide")

    @api.depends("line_id", "line_id.line_approval_state", "event_type")
    def _compute_can_decide(self):
        is_supervisor = self.env.user.has_group(
            "justech_l10n_do_base.group_justech_do_fiscal_manager"
        )
        for audit in self:
            pending = (
                audit.line_id
                and audit.line_id.line_approval_state == "pending"
                and audit.event_type in ("exclude", "submit_approval")
            )
            audit.can_decide = bool(is_supervisor and pending)
            if not audit.line_id or audit.line_id.line_approval_state != "pending":
                audit.permission_hint = ""
            elif is_supervisor:
                audit.permission_hint = ""
            else:
                audit.permission_hint = _(
                    "Solo el supervisor fiscal puede aprobar, rechazar o solicitar corrección."
                )

    def _require_decision_access(self):
        self.ensure_one()
        if not self.can_decide:
            hint = self.permission_hint or _(
                "No tiene permisos para decidir sobre este registro."
            )
            raise AccessError(hint)

    def action_audit_approve(self):
        self._require_decision_access()
        lines = self.mapped("line_id").filtered(
            lambda l: l.line_approval_state == "pending"
        )
        if not lines:
            raise UserError(_("No hay líneas pendientes de aprobación."))
        lines.action_approve_line()
        return True

    def action_audit_reject(self):
        self.ensure_one()
        self._require_decision_access()
        if not self.line_id:
            raise UserError(_("Este registro de bitácora no tiene línea vinculada."))
        return self.line_id.action_reject_line()

    def action_audit_request_correction(self):
        self.ensure_one()
        self._require_decision_access()
        if not self.line_id:
            raise UserError(_("Este registro de bitácora no tiene línea vinculada."))
        return self.line_id.action_request_correction_line()
