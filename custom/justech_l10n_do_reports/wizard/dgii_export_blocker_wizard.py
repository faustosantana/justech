# -*- coding: utf-8 -*-
from odoo import _, fields, models


class JustechDoDgiiExportBlockerWizard(models.TransientModel):
    _name = "justech.do.dgii.export.blocker.wizard"
    _description = "Asistente — bloqueo generación Excel DGII"

    report_id = fields.Many2one(
        "justech.do.fiscal.report",
        string="Reporte",
        required=True,
        readonly=True,
    )
    report_state = fields.Char(string="Estado reporte", readonly=True)
    valid_count = fields.Integer(string="Documentos válidos", readonly=True)
    pending_approval_count = fields.Integer(string="Pendientes aprobación", readonly=True)
    incomplete_count = fields.Integer(string="Incompletos", readonly=True)
    not_loaded = fields.Boolean(string="Sin líneas cargadas", readonly=True)
    needs_approval = fields.Boolean(string="Requiere aprobación", readonly=True)
    no_valid = fields.Boolean(string="Sin válidos", readonly=True)
    wrong_state = fields.Boolean(string="Estado incorrecto", readonly=True)
    summary_html = fields.Html(string="Resumen", compute="_compute_summary_html")

    def _compute_summary_html(self):
        for wiz in self:
            lines = []
            lines.append(
                _("<p><strong>No es posible generar el Excel %(type)s.</strong></p>")
                % {"type": wiz.report_id.report_type}
            )
            lines.append("<ul>")
            if wiz.valid_count:
                lines.append(
                    _("<li>✓ %(n)s documento(s) válido(s)</li>") % {"n": wiz.valid_count}
                )
            else:
                lines.append(_("<li>✗ No hay documentos válidos para exportar</li>"))
            if wiz.pending_approval_count:
                lines.append(
                    _(
                        "<li>✗ %(n)s documento(s) aún no han sido aprobados por el supervisor</li>"
                    )
                    % {"n": wiz.pending_approval_count}
                )
            if wiz.incomplete_count:
                lines.append(
                    _("<li>✗ %(n)s documento(s) incompletos (no exportables)</li>")
                    % {"n": wiz.incomplete_count}
                )
            if wiz.not_loaded:
                lines.append(
                    _("<li>✗ La revisión fiscal no tiene líneas cargadas — valide el período primero</li>")
                )
            if wiz.wrong_state and not wiz.needs_approval:
                lines.append(
                    _(
                        "<li>✗ El reporte está en estado «%(state)s» — debe estar Validado o Aprobado</li>"
                    )
                    % {"state": wiz.report_state}
                )
            lines.append("</ul>")
            lines.append(_("<p><strong>Acciones disponibles:</strong></p>"))
            wiz.summary_html = "".join(lines)

    def action_go_fiscal_review(self):
        self.ensure_one()
        return self.report_id.action_open_fiscal_review()

    def action_go_pending_tray(self):
        self.ensure_one()
        return self.report_id.action_open_pending_tray()

    def action_view_blocked_documents(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Documentos bloqueantes"),
            "res_model": "justech.do.fiscal.report.line",
            "view_mode": "list",
            "domain": [
                ("report_id", "=", self.report_id.id),
                "|",
                ("fiscal_state", "=", "incomplete"),
                ("line_approval_state", "=", "pending"),
            ],
            "context": {
                "list_view_ref": "justech_l10n_do_reports.view_justech_do_fiscal_report_line_review_tree",
            },
            "target": "current",
        }
