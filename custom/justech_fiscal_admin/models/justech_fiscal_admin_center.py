# -*- coding: utf-8 -*-
"""Centro de Administración Fiscal Justech — hub Enterprise."""
import json

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError


def _status_badge(ok):
    if ok:
        return '<span class="badge text-bg-success">OK</span>'
    return '<span class="badge text-bg-danger">Atención</span>'


class JustechFiscalAdminCenter(models.TransientModel):
    _name = "justech.fiscal.admin.center"
    _description = "Centro de Administración Fiscal Justech"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    stack_json = fields.Text(readonly=True)
    health_json = fields.Text(readonly=True)
    dashboard_html = fields.Html(compute="_compute_dashboard_html", sanitize=False)
    last_refresh = fields.Datetime(readonly=True)
    health_ok = fields.Boolean(readonly=True)
    issue_count = fields.Integer(readonly=True)
    warning_count = fields.Integer(readonly=True)
    motor_status = fields.Char(readonly=True)
    provider_status = fields.Char(readonly=True)
    reports_status = fields.Char(readonly=True)

    payments_json = fields.Text(readonly=True)

    @api.depends("stack_json", "health_json", "payments_json", "company_id")
    def _compute_dashboard_html(self):
        svc = self.env["justech.fiscal.admin.service"]
        for rec in self:
            if not rec.stack_json:
                rec.dashboard_html = Markup("<p class='text-muted'>Pulse Actualizar.</p>")
                continue
            stack = json.loads(rec.stack_json)
            health = json.loads(rec.health_json) if rec.health_json else {}
            modules_html = "".join(
                f"<li><strong>{m['name']}</strong> — {m['state']} ({m['version']})</li>"
                for m in stack.get("modules", [])
            )
            features_html = "".join(
                f"<li>{f['name']}: {'ON' if f['enabled'] else 'OFF'}</li>"
                for f in stack.get("features", [])
            )
            issues = "".join(f"<li class='text-danger'>{i}</li>" for i in health.get("issues", []))
            warns = "".join(f"<li class='text-warning'>{w}</li>" for w in health.get("warnings", []))
            recs = "".join(
                f"<li class='text-info'>{r}</li>" for r in health.get("recommendations", [])
            )
            multi = svc.multi_company_summary()
            multi_html = "".join(
                f"<tr><td>{r['name']}</td><td>{_status_badge(r['fiscal_enabled'])}</td>"
                f"<td>{_status_badge(r['health_ok'])}</td><td>{r['issues']}</td><td>{r['warnings']}</td></tr>"
                for r in multi
            )
            pay = json.loads(rec.payments_json) if rec.payments_json else {}
            pay_inc = "".join(
                f"<li class='text-warning'>{i}</li>" for i in pay.get("inconsistencies", [])
            )
            banks_html = "".join(
                f"<li>{b.get('code')} — {b.get('name')} ({b.get('type')})</li>"
                for b in pay.get("banks", [])
            )
            rec.dashboard_html = Markup(
                f"""
                <div class="justech-fiscal-admin">
                    <div class="row g-3 mb-3">
                        <div class="col-md-3"><div class="card p-3"><h5>Motor NCF</h5><p>{rec.motor_status}</p></div></div>
                        <div class="col-md-3"><div class="card p-3"><h5>Provider</h5><p>{rec.provider_status}</p></div></div>
                        <div class="col-md-3"><div class="card p-3"><h5>Reportes DGII</h5><p>{rec.reports_status}</p></div></div>
                        <div class="col-md-3"><div class="card p-3"><h5>Salud</h5><p>{_status_badge(rec.health_ok)} {rec.issue_count} errores / {rec.warning_count} adv.</p></div></div>
                    </div>
                    <h4>Pagos y Retenciones</h4>
                    <ul>
                        <li>Estado: {pay.get('standard_status', '—')}</li>
                        <li>Feature flag: {'ON' if pay.get('feature_enabled') else 'OFF'}</li>
                        <li>Catálogo activo: {pay.get('catalog_active', 0)} / {pay.get('catalog_total', 0)}</li>
                        <li>Impuestos reutilizados: {pay.get('taxes_reused', 0)}</li>
                        <li>Pagos con retención (histórico): {pay.get('payments_with_withholding', 0)}</li>
                        <li>Líneas retención: {pay.get('withholding_lines', 0)}</li>
                    </ul>
                    <p><strong>Bancos / cajas</strong></p><ul>{banks_html or '<li>—</li>'}</ul>
                    <ul>{pay_inc}</ul>
                    <h4>Módulos del stack fiscal</h4><ul>{modules_html}</ul>
                    <h4>Feature Flags</h4><ul>{features_html}</ul>
                    <h4>Multiempresa</h4>
                    <table class="table table-sm"><thead><tr><th>Empresa</th><th>Fiscal</th><th>Salud</th><th>Errores</th><th>Adv.</th></tr></thead><tbody>{multi_html}</tbody></table>
                    <h4>Alertas</h4><ul>{issues}{warns}</ul>
                    <h4>Recomendaciones</h4><ul>{recs}</ul>
                </div>
                """
            )

    def action_open(self):
        self.ensure_one()
        self._refresh()
        return {
            "type": "ir.actions.act_window",
            "name": _("Centro de Administración Fiscal Justech"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def open_for_user(self):
        center = self.create({"company_id": self.env.company.id})
        center._refresh()
        return center.action_open()

    def _refresh(self):
        svc = self.env["justech.fiscal.admin.service"]
        stack = svc.stack_status(self.company_id)
        health = svc.health_check(self.company_id)
        payments = svc.payments_withholding_status(self.company_id)
        self.write(
            {
                "stack_json": json.dumps(stack, ensure_ascii=False, default=str),
                "health_json": json.dumps(
                    {
                        "ok": health["ok"],
                        "issues": health["issues"],
                        "warnings": health["warnings"],
                        "recommendations": health["recommendations"],
                        "gl_balanced": health["gl_balanced"],
                    },
                    ensure_ascii=False,
                    default=str,
                ),
                "payments_json": json.dumps(payments, ensure_ascii=False, default=str),
                "last_refresh": fields.Datetime.now(),
                "health_ok": health["ok"],
                "issue_count": len(health["issues"]),
                "warning_count": len(health["warnings"]),
                "motor_status": _("Activo") if stack.get("motor_active") else _("Inactivo"),
                "provider_status": _("Solo lectura histórica"),
                "reports_status": _("Activo") if stack.get("reports_active") else _("Inactivo"),
            }
        )

    def action_refresh(self):
        self._refresh()
        return self.action_open()

    def action_run_health_check(self):
        self._refresh()
        health = json.loads(self.health_json)
        title = _("Salud OK") if health.get("ok") else _("Problemas detectados")
        body = "\n".join(health.get("issues", []) + health.get("warnings", []))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": body or _("Sin incidencias."),
                "type": "success" if health.get("ok") else "warning",
                "sticky": not health.get("ok"),
            },
        }

    def action_open_feature_flags(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Feature Flags Fiscales"),
            "res_model": "justech.fiscal.feature.flag",
            "view_mode": "list,form",
            "domain": [
                "|",
                ("company_id", "=", False),
                ("company_id", "=", self.company_id.id),
            ],
            "context": {"default_company_id": self.company_id.id},
        }

    def action_open_ncf_ranges(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Rangos NCF"),
            "res_model": "justech.do.ncf.range",
            "view_mode": "list,form",
            "domain": [("company_id", "=", self.company_id.id)],
        }

    def action_open_diagnostic(self):
        wizard = self.env["justech.do.fiscal.diagnostic.wizard"].create(
            {"company_id": self.company_id.id}
        )
        wizard.action_run_scan()
        return {
            "type": "ir.actions.act_window",
            "name": _("Diagnóstico Fiscal"),
            "res_model": "justech.do.fiscal.diagnostic.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_open_dgii_reports(self):
        mod = self.env["ir.module.module"].search(
            [("name", "=", "justech_l10n_do_reports"), ("state", "=", "installed")],
            limit=1,
        )
        if not mod:
            raise UserError(_("Instale el módulo Justech Reportes DGII."))
        return self.env.ref("justech_l10n_do_reports.action_justech_do_fiscal_report").read()[0]

    def action_open_ncf_admin(self):
        return self.env["justech.do.ncf.admin.center"].open_for_user(self.env)
