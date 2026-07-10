# -*- coding: utf-8 -*-
"""Servicio de administración fiscal — stack, salud, integridad."""
from odoo import _, fields, models


FISCAL_MODULES = (
    "justech_l10n_do_base",
    "justech_l10n_do_ncf",
    "justech_l10n_do_reports",
    "justech_l10n_do_dashboard",
    "justech_l10n_do_payments_withholding",
    "justech_fiscal_admin",
)


class JustechFiscalAdminService(models.AbstractModel):
    _name = "justech.fiscal.admin.service"
    _description = "Justech Fiscal Administration Service"

    def stack_status(self, company=None):
        company = company or self.env.company
        Module = self.env["ir.module.module"]
        rows = []
        for name in FISCAL_MODULES:
            mod = Module.search([("name", "=", name)], limit=1)
            rows.append(
                {
                    "name": name,
                    "state": mod.state if mod else "uninstalled",
                    "version": mod.latest_version if mod else "—",
                    "installed": mod.state == "installed" if mod else False,
                }
            )
        flags = self.env["justech.fiscal.feature.flag"]
        feature_rows = []
        for flag in flags.search(
            ["|", ("company_id", "=", False), ("company_id", "=", company.id)],
            order="sequence",
        ):
            effective = flags.is_enabled(flag.code, company)
            feature_rows.append(
                {
                    "code": flag.code,
                    "name": flag.name,
                    "category": flag.category,
                    "enabled": effective,
                    "readonly": flag.readonly_flag,
                }
            )
        return {
            "company": {"id": company.id, "name": company.name},
            "modules": rows,
            "features": feature_rows,
            "fiscal_enabled": company.justech_do_fiscal_enabled,
            "motor_active": company.justech_do_fiscal_enabled
            and flags.is_enabled("ncf_motor", company),
            "provider_mode": "historical_read_only",
            "reports_active": flags.is_enabled("dgii_reports", company),
            "dashboard_active": flags.is_enabled("fiscal_dashboard", company),
        }

    def health_check(self, company=None):
        company = company or self.env.company
        issues = []
        warnings = []
        recommendations = []

        if company.country_id.code != "DO":
            warnings.append(_("Empresa sin país República Dominicana."))

        if not company.justech_do_fiscal_enabled:
            issues.append(_("Motor fiscal desactivado para esta empresa."))

        sale_j = self.env["account.journal"].search(
            [("company_id", "=", company.id), ("type", "=", "sale")], limit=1
        )
        if sale_j:
            if sale_j.l10n_latam_use_documents:
                issues.append(
                    _("Diario de ventas con documentos LATAM activos — riesgo doble motor Adel.")
                )
            if not sale_j.justech_do_use_ncf:
                warnings.append(_("Diario de ventas sin NCF Justech activo."))

        findings = []
        if "justech.do.ncf.diagnostic.service" in self.env:
            findings = self.env["justech.do.ncf.diagnostic.service"].run_full_scan(company)
            for f in findings:
                if f.get("severity") == "error":
                    issues.append(f.get("title", f.get("code", "?")))
                elif f.get("severity") == "warning":
                    warnings.append(f.get("title", f.get("code", "?")))

        cr = self.env.cr
        cr.execute(
            "SELECT COALESCE(SUM(debit),0), COALESCE(SUM(credit),0) "
            "FROM account_move_line aml JOIN account_move am ON am.id=aml.move_id WHERE am.state='posted'"
        )
        d, c = cr.fetchone()
        gl_ok = float(d) == float(c)
        if not gl_ok:
            issues.append(_("Libro mayor desbalanceado."))

        dup_groups = []
        if "justech.do.ncf.duplicate.service" in self.env:
            dup_groups = self.env["justech.do.ncf.duplicate.service"].find_duplicate_groups_v2(
                company
            )
            if dup_groups:
                issues.append(_("Duplicados NCF detectados: %(n)s grupos.", n=len(dup_groups)))

        if not warnings and not issues:
            recommendations.append(_("Stack fiscal operando correctamente."))
        if sale_j and sale_j.l10n_latam_use_documents:
            recommendations.append(
                _("Desactivar 'Usar documentos' en diario de ventas para evitar doble asignación.")
            )

        return {
            "ok": not issues,
            "gl_balanced": gl_ok,
            "gl_debit": float(d),
            "gl_credit": float(c),
            "issues": issues,
            "warnings": warnings,
            "recommendations": recommendations,
            "diagnostic_count": len(findings),
            "duplicate_groups": len(dup_groups),
        }

    def multi_company_summary(self):
        companies = self.env["res.company"].search([])
        rows = []
        for co in companies:
            hc = self.health_check(co)
            rows.append(
                {
                    "id": co.id,
                    "name": co.name,
                    "fiscal_enabled": co.justech_do_fiscal_enabled,
                    "health_ok": hc["ok"],
                    "issues": len(hc["issues"]),
                    "warnings": len(hc["warnings"]),
                }
            )
        return rows

    def sequence_validation(self, company=None):
        company = company or self.env.company
        Range = self.env["justech.do.ncf.range"]
        rows = []
        today = fields.Date.context_today(self)
        for rng in Range.search([("company_id", "=", company.id)]):
            rows.append(
                {
                    "prefix": rng.prefix,
                    "name": rng.name,
                    "state": rng.state,
                    "next_sequence": rng.next_sequence,
                    "remaining": max(0, rng.sequence_end - rng.next_sequence + 1),
                    "expired": rng.date_to < today if rng.date_to else False,
                }
            )
        return rows

    def payments_withholding_status(self, company=None):
        """Estado read-only Pagos y Retenciones."""
        company = company or self.env.company
        Module = self.env["ir.module.module"]
        wh_pkg = Module.search([("name", "=", "justech_l10n_do_payments_withholding")], limit=1)
        flags = self.env["justech.fiscal.feature.flag"]

        catalog_count = catalog_active = wh_lines = wh_payments = 0
        banks = []
        inconsistencies = []
        taxes_reused = 0

        if "justech.do.withholding.catalog" in self.env:
            Catalog = self.env["justech.do.withholding.catalog"]
            catalog_count = Catalog.search_count([("company_id", "=", company.id)])
            catalog_active = Catalog.search_count(
                [("company_id", "=", company.id), ("active", "=", True)]
            )
            taxes_reused = Catalog.search_count(
                [("company_id", "=", company.id), ("tax_id", "!=", False)]
            )
        if "justech.payment.withholding.line" in self.env:
            wh_lines = self.env["justech.payment.withholding.line"].search_count(
                [("company_id", "=", company.id)]
            )
        if "justech_withholding_total" in self.env["account.payment"]._fields:
            wh_payments = self.env["account.payment"].search_count(
                [
                    ("company_id", "=", company.id),
                    ("justech_withholding_total", ">", 0),
                    ("state", "in", ("paid", "in_process", "posted")),
                ]
            )

        for j in self.env["account.journal"].search(
            [("company_id", "=", company.id), ("type", "in", ("bank", "cash"))]
        ):
            banks.append({"code": j.code, "name": j.name, "type": j.type})

        if not wh_pkg or wh_pkg.state != "installed":
            inconsistencies.append(_("Módulo justech_l10n_do_payments_withholding no instalado."))
        elif not flags.is_enabled("payments_withholding", company):
            inconsistencies.append(_("Feature flag Pagos y Retenciones desactivado."))
        if catalog_count == 0 and wh_pkg and wh_pkg.state == "installed":
            inconsistencies.append(_("Catálogo retenciones vacío — ejecute sincronización."))

        standard_status = "activo" if wh_pkg and wh_pkg.state == "installed" and not inconsistencies else "pendiente"

        return {
            "modules": {
                "payments_withholding": wh_pkg.state if wh_pkg else "missing",
            },
            "feature_enabled": flags.is_enabled("payments_withholding", company),
            "catalog_total": catalog_count,
            "catalog_active": catalog_active,
            "taxes_reused": taxes_reused,
            "withholding_lines": wh_lines,
            "payments_with_withholding": wh_payments,
            "banks": banks,
            "inconsistencies": inconsistencies,
            "standard_status": standard_status,
        }
