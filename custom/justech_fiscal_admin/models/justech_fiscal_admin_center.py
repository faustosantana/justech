# -*- coding: utf-8 -*-
"""Centro de Administración Fiscal Justech — hub Enterprise."""
import json

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError


def _status_icon(ok, warn=False):
    if ok:
        return "🟢"
    if warn:
        return "🟡"
    return "🔴"


def _progress_bar(used_pct):
    pct = min(100, max(0, int(used_pct or 0)))
    color = "success" if pct < 70 else ("warning" if pct < 90 else "danger")
    return (
        f'<div class="progress justech-fiscal-progress" style="height:22px">'
        f'<div class="progress-bar bg-{color}" role="progressbar" '
        f'style="width:{pct}%" aria-valuenow="{pct}" aria-valuemin="0" aria-valuemax="100">'
        f"{pct}%</div></div>"
    )


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
    ncf_json = fields.Text(readonly=True)

    @api.depends("stack_json", "health_json", "payments_json", "ncf_json", "company_id")
    def _compute_dashboard_html(self):
        svc = self.env["justech.fiscal.admin.service"]
        for rec in self:
            if not rec.stack_json:
                rec.dashboard_html = Markup("<p class='text-muted'>Pulse Actualizar.</p>")
                continue
            stack = json.loads(rec.stack_json)
            health = json.loads(rec.health_json) if rec.health_json else {}
            pay = json.loads(rec.payments_json) if rec.payments_json else {}
            ncf = json.loads(rec.ncf_json) if rec.ncf_json else {}

            motor_ok = stack.get("motor_active")
            reports_ok = stack.get("reports_active")
            pay_ok = pay.get("standard_status") == "activo" and pay.get("wizard_unified")
            health_warn = not health.get("ok") and health.get("warnings")

            modules_html = "".join(
                f"<li>{_status_icon(m['state']=='installed')} <strong>{m['name']}</strong> "
                f"— {m['state']} ({m['version']})</li>"
                for m in stack.get("modules", [])
            )
            features_html = "".join(
                f"<li>{_status_icon(f['enabled'], warn=not f['enabled'] and not f.get('readonly'))} "
                f"{f['name']}: {'Activado' if f['enabled'] else 'Desactivado'}</li>"
                for f in stack.get("features", [])
            )
            issues = "".join(f"<li>{_status_icon(False)} {i}</li>" for i in health.get("issues", []))
            warns = "".join(f"<li>{_status_icon(False, warn=True)} {w}</li>" for w in health.get("warnings", []))
            recs = "".join(
                f"<li>{_status_icon(True, warn=True)} {r}</li>" for r in health.get("recommendations", [])
            )
            multi = svc.multi_company_summary()
            multi_html = "".join(
                f"<tr><td>{r['name']}</td>"
                f"<td>{_status_icon(r['fiscal_enabled'])} {'Sí' if r['fiscal_enabled'] else 'No'}</td>"
                f"<td>{_status_icon(r['health_ok'], warn=not r['health_ok'] and r['warnings']==0)}</td>"
                f"<td>{r['issues']}</td><td>{r['warnings']}</td></tr>"
                for r in multi
            )
            pay_inc = "".join(
                f"<li>{_status_icon(False, warn=True)} {i}</li>" for i in pay.get("inconsistencies", [])
            )
            ncf_rows = "".join(
                f"<tr><td>{r['prefix']}</td><td>{r['state']}</td>"
                f"<td>{r['remaining']}/{r['capacity']}</td>"
                f"<td>{_progress_bar(r['used_pct'])}</td>"
                f"<td>{_status_icon(r['status']=='ok', warn=r['status']=='warning')}</td></tr>"
                for r in ncf.get("ranges", [])
            )
            ncf_alerts = "".join(
                f"<li>{_status_icon(False, warn=True)} {a}</li>" for a in ncf.get("alerts", [])
            )

            rec.dashboard_html = Markup(
                f"""
                <div class="justech-fiscal-admin">
                    <div class="row g-3 mb-3">
                        <div class="col-md-3"><div class="card p-3">
                            <h5>{_status_icon(motor_ok)} Motor NCF</h5>
                            <p>{rec.motor_status}</p></div></div>
                        <div class="col-md-3"><div class="card p-3">
                            <h5>{_status_icon(True, warn=True)} Provider</h5>
                            <p>{rec.provider_status}</p></div></div>
                        <div class="col-md-3"><div class="card p-3">
                            <h5>{_status_icon(reports_ok)} Reportes DGII</h5>
                            <p>{rec.reports_status}</p></div></div>
                        <div class="col-md-3"><div class="card p-3">
                            <h5>{_status_icon(health.get('ok'), warn=health_warn)} Salud Fiscal</h5>
                            <p>{rec.issue_count} errores · {rec.warning_count} advertencias</p>
                            <p class="mb-0">GL: {_status_icon(health.get('gl_balanced'))} {'Balanceado' if health.get('gl_balanced') else 'Desbalanceado'}</p>
                        </div></div>
                    </div>
                    <div class="row g-3 mb-3">
                        <div class="col-md-6"><div class="card p-3">
                            <h5>{_status_icon(pay_ok)} Pagos y Retenciones</h5>
                            <ul class="mb-0">
                                <li>Wizard unificado: {'Sí' if pay.get('wizard_unified') else 'No'}</li>
                                <li>Catálogo activo: {pay.get('catalog_active', 0)} / {pay.get('catalog_total', 0)}</li>
                                <li>Pagos con retención: {pay.get('payments_with_withholding', 0)}</li>
                                <li>Líneas retención: {pay.get('withholding_lines', 0)}</li>
                            </ul>
                            <ul>{pay_inc}</ul>
                        </div></div>
                        <div class="col-md-6"><div class="card p-3">
                            <h5>{_status_icon(not ncf.get('alerts'), warn=bool(ncf.get('alerts')))} Consumo NCF</h5>
                            <p>Disponibles totales: <strong>{ncf.get('total_remaining', 0)}</strong></p>
                            <table class="table table-sm mb-0">
                                <thead><tr><th>Prefijo</th><th>Estado</th><th>Restantes</th><th>Uso</th><th></th></tr></thead>
                                <tbody>{ncf_rows or '<tr><td colspan="5">Sin rangos</td></tr>'}</tbody>
                            </table>
                            <ul>{ncf_alerts}</ul>
                        </div></div>
                    </div>
                    <h4>Módulos del stack fiscal</h4><ul>{modules_html}</ul>
                    <h4>Feature Flags</h4><ul>{features_html}</ul>
                    <h4>Multiempresa</h4>
                    <table class="table table-sm"><thead><tr><th>Empresa</th><th>Fiscal</th><th>Salud</th><th>Errores</th><th>Adv.</th></tr></thead><tbody>{multi_html}</tbody></table>
                    <h4>Alertas y diagnóstico</h4><ul>{issues}{warns}</ul>
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
        ncf = svc.ncf_consumption_summary(self.company_id)
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
                "ncf_json": json.dumps(ncf, ensure_ascii=False, default=str),
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

    def action_open_withholding_catalog(self):
        mod = self.env["ir.module.module"].search(
            [("name", "=", "justech_l10n_do_payments_withholding"), ("state", "=", "installed")],
            limit=1,
        )
        if not mod:
            raise UserError(_("Instale el módulo Pagos y Retenciones Justech."))
        return self.env.ref(
            "justech_l10n_do_payments_withholding.action_justech_withholding_catalog"
        ).read()[0]

    def action_sync_withholding_catalog(self):
        if "justech.do.withholding.catalog" not in self.env:
            raise UserError(_("Catálogo de retenciones no disponible."))
        self.env["justech.do.withholding.catalog"].sync_catalog_from_taxes(self.company_id)
        self._refresh()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Catálogo sincronizado"),
                "message": _("Retenciones actualizadas desde impuestos l10n_do."),
                "type": "success",
            },
        }
