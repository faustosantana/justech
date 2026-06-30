# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class JustechDoDgiiReportExcludeWizard(models.TransientModel):
    _name = "justech.do.dgii.report.exclude.wizard"
    _description = "Excluir documentos del reporte DGII"

    report_id = fields.Many2one(
        "justech.do.fiscal.report",
        string="Reporte",
        required=True,
        ondelete="cascade",
    )
    line_ids = fields.Many2many(
        "justech.do.fiscal.report.line",
        "dgii_excl_wiz_line_rel",
        "wizard_id",
        "line_id",
        string="Líneas",
        required=True,
    )
    reason = fields.Text(string="Motivo de exclusión", required=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids", [])
        if active_model == "justech.do.fiscal.report.line" and active_ids:
            lines = self.env["justech.do.fiscal.report.line"].browse(active_ids)
            res["line_ids"] = [(6, 0, lines.ids)]
            if lines:
                res["report_id"] = lines[0].report_id.id
        return res

    def action_confirm_exclude(self):
        self.ensure_one()
        if not self.reason.strip():
            raise UserError(_("Debe indicar el motivo de exclusión fiscal."))
        report = self.report_id
        report._check_editable()
        now = fields.Datetime.now()
        for line in self.line_ids:
            move = line.move_id
            line.write(
                {
                    "include_in_report": False,
                    "manual_exclusion": True,
                    "exclusion_reason": self.reason,
                    "fiscal_state": "excluded",
                    "line_approval_state": "pending",
                    "excluded_by_id": self.env.user.id,
                    "excluded_at": now,
                }
            )
            if move:
                move.write(
                    {
                        "justech_do_include_in_dgii": False,
                        "justech_do_dgii_exclusion_reason": self.reason,
                        "justech_do_dgii_fiscal_state": "excluded",
                    }
                )
                move.message_post(
                    body=_(
                        "Excluido fiscalmente del reporte DGII %(type)s por %(user)s. "
                        "Motivo: %(reason)s"
                    )
                    % {
                        "type": report.report_type,
                        "user": self.env.user.name,
                        "reason": self.reason,
                    }
                )
            report.message_post(
                body=_(
                    "Exclusión manual: %(doc)s — %(reason)s"
                )
                % {"doc": line.move_name, "reason": self.reason}
            )
            report._log_audit(
                "exclude",
                self.reason,
                move=move,
                line=line,
            )
        if report.state in ("draft", "validated", "rejected"):
            report.write({"state": "pending_approval"})
            report.action_submit_for_approval()
        elif report.state == "pending_approval":
            report.action_submit_for_approval()
        return {"type": "ir.actions.act_window_close"}


class JustechDoDgiiReportRejectWizard(models.TransientModel):
    _name = "justech.do.dgii.report.reject.wizard"
    _description = "Rechazar exclusiones DGII"

    report_id = fields.Many2one(
        "justech.do.fiscal.report",
        string="Reporte",
        required=True,
    )
    comment = fields.Text(string="Comentario", required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        if not self.comment.strip():
            raise UserError(_("Debe indicar el motivo del rechazo."))
        self.report_id._apply_rejection(self.comment)
        return {"type": "ir.actions.act_window_close"}
