from odoo import api, fields, models, _
from odoo.exceptions import UserError


class JustechAdminCompanyActivationService(models.AbstractModel):
    _name = "justech.admin.company.activation.service"
    _description = "Activación funcional Justech por empresa"

    @api.model
    def build_preview(self, line, operation, new_engine=None):
        line.ensure_one()
        module = line.module_id
        company = line.company_id
        before = {
            "estado": line.functional_state,
            "motor": line.fiscal_engine,
            "empresa": company.name,
            "modulo": module.functional_name,
        }
        after = dict(before)
        risks = []
        if operation == "activate":
            after["estado"] = "active"
            if module.fiscal_engine_capable and new_engine:
                after["motor"] = new_engine
            elif module.fiscal_engine_capable and line.fiscal_engine == "none":
                after["motor"] = "traditional_ncf"
            risks.append(_("Se habilitarán operaciones nuevas del módulo en esta empresa."))
        elif operation == "deactivate":
            after["estado"] = "inactive"
            risks.append(_("Se bloquearán nuevas operaciones; el histórico se conserva."))
            if module.is_critical:
                # ensure another company still has fiscal if needed — soft check
                others = self.env["justech.admin.module.company"].search(
                    [
                        ("module_id", "=", module.id),
                        ("id", "!=", line.id),
                        ("functional_state", "=", "active"),
                    ]
                )
                if not others and module.is_critical:
                    risks.append(
                        _("Advertencia: ninguna otra empresa tendrá este módulo crítico activo.")
                    )
        elif operation == "engine":
            if not module.fiscal_engine_capable:
                raise UserError(_("Este módulo no admite selección de motor fiscal."))
            if not new_engine:
                raise UserError(_("Seleccione el motor fiscal destino."))
            # incompatible engines same company: only one active engine value
            after["motor"] = new_engine
            after["estado"] = "active"
            risks.append(_("No se permite emitir con dos motores incompatibles en la misma empresa."))
        return {
            "before": before,
            "after": after,
            "risks": "\n".join(risks),
            "no_impact": _(
                "No afecta histórico, NCF emitidos, pagos históricos ni contabilidad publicada."
            ),
            "rollback": _("Revertir el estado funcional desde la misma consola."),
        }

    @api.model
    def apply(self, line, operation, new_engine=None):
        self.env["justech.admin.center.auth.service"].require_session()
        preview = self.build_preview(line, operation, new_engine=new_engine)
        module = line.module_id
        company = line.company_id
        vals = {
            "last_change_at": fields.Datetime.now(),
            "last_change_uid": self.env.uid,
        }
        if operation == "activate":
            vals["functional_state"] = "active"
            engine = new_engine or (
                line.fiscal_engine if line.fiscal_engine != "none" else "traditional_ncf"
            )
            if module.fiscal_engine_capable:
                vals["fiscal_engine"] = engine
                self._unify_company_engine(company, engine, prefer_line=line)
            self._sync_company_flags(module, company, enabled=True)
            self._sync_fiscal_enabled(company, enabled=True)
        elif operation == "deactivate":
            vals["functional_state"] = "inactive"
            self._sync_company_flags(module, company, enabled=False)
        elif operation == "engine":
            vals["fiscal_engine"] = new_engine
            vals["functional_state"] = "active"
            self._unify_company_engine(company, new_engine, prefer_line=line)
            self._sync_company_flags(module, company, enabled=True)
            self._sync_fiscal_enabled(company, enabled=True)
        line.write(vals)
        # rollup module functional_state
        active_any = self.env["justech.admin.module.company"].search_count(
            [("module_id", "=", module.id), ("functional_state", "=", "active")]
        )
        module.write({"functional_state": "active" if active_any else "inactive"})
        self.env["justech.admin.audit.log"].sudo().log_simple(
            summary=_("%s / %s → %s") % (module.functional_name, company.name, operation),
            operation=operation,
            module_id=module.id,
            state_before=str(preview["before"]),
            state_after=str(preview["after"]),
            reason=preview["risks"],
        )
        return preview

    @api.model
    def _unify_company_engine(self, company, engine, prefer_line=None):
        """One fiscal engine per company across all engine-capable submodules."""
        Line = self.env["justech.admin.module.company"]
        domain = [
            ("company_id", "=", company.id),
            ("module_id.fiscal_engine_capable", "=", True),
        ]
        lines = Line.search(domain)
        for other in lines:
            vals = {"fiscal_engine": engine, "functional_state": "active"}
            if prefer_line and other.id == prefer_line.id:
                continue
            other.write(vals)


    @api.model
    def _sync_company_flags(self, module, company, enabled):
        codes = [c.strip() for c in (module.feature_flag_codes or "").split(",") if c.strip()]
        if not codes or "justech.fiscal.feature.flag" not in self.env:
            return
        Flag = self.env["justech.fiscal.feature.flag"].sudo()
        for code in codes:
            flag = Flag.search([("code", "=", code), ("company_id", "=", company.id)], limit=1)
            if not flag:
                flag = Flag.search([("code", "=", code), ("company_id", "=", False)], limit=1)
            if not flag:
                continue
            vals = {}
            if "is_enabled" in Flag._fields:
                # company-specific: write on company-bound copy if possible
                if flag.company_id:
                    vals["is_enabled"] = enabled
                    flag.write(vals)
                else:
                    # create/update company override if model allows
                    existing = Flag.search([("code", "=", code), ("company_id", "=", company.id)], limit=1)
                    if existing:
                        existing.write({"is_enabled": enabled})
                    else:
                        try:
                            Flag.create({"code": code, "company_id": company.id, "is_enabled": enabled, "name": code})
                        except Exception:
                            flag.write({"is_enabled": enabled})
            elif "enabled" in Flag._fields:
                flag.write({"enabled": enabled})

    @api.model
    def _sync_fiscal_enabled(self, company, enabled):
        if "justech_do_fiscal_enabled" in company._fields:
            company.sudo().write({"justech_do_fiscal_enabled": enabled})

    @api.model
    def ensure_lines_for_module(self, module):
        """Create company lines for all companies when module is installed."""
        if module.technical_state != "installed":
            return
        Company = self.env["res.company"].sudo()
        Line = self.env["justech.admin.module.company"].sudo()
        for company in Company.search([]):
            existing = Line.search(
                [("module_id", "=", module.id), ("company_id", "=", company.id)], limit=1
            )
            if existing:
                continue
            state = "unconfigured"
            engine = "none"
            if module.activation_scope == "global" and module.functional_state == "active":
                state = "active"
            if module.fiscal_engine_capable and getattr(company, "justech_do_fiscal_enabled", False):
                state = "active"
                engine = "traditional_ncf"
            Line.create(
                {
                    "module_id": module.id,
                    "company_id": company.id,
                    "functional_state": state,
                    "fiscal_engine": engine if module.fiscal_engine_capable else "none",
                }
            )
