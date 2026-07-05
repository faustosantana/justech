from datetime import date

from odoo import _, api, fields, models

from ..exceptions import JustechLicenseError


class JustechLicenseService(models.AbstractModel):
    _name = "justech.license.service"
    _description = "Justech License Public API"

    API_VERSION = 1

    # ------------------------------------------------------------------ API
    @api.model
    def get_api_version(self):
        """Return stable public API semver major version."""
        return self.API_VERSION

    @api.model
    def is_active(self, feature_code, company=None):
        company = company or self.env.company
        feature = self._get_feature_record(feature_code)
        if not feature:
            return False
        if feature.always_on:
            return True
        if not self._company_has_valid_license(company):
            return False
        if feature.license_required and not self._feature_granted_to_company(
            feature, company
        ):
            return False
        return self._feature_is_active_for_company(feature.id, company.id)

    @api.model
    def require_active(self, feature_code, company=None):
        if not self.is_active(feature_code, company=company):
            raise JustechLicenseError(
                _("Feature '%(code)s' is not licensed or active for this company.")
                % {"code": feature_code}
            )

    @api.model
    def get_feature(self, feature_code):
        return self._get_feature_record(feature_code)

    @api.model
    def validate_license(self, key=None, feature_code=None, company=None):
        company = company or self.env.company
        result = {
            "valid": False,
            "reason": "invalid_key",
            "expires": False,
            "tier": False,
        }
        if not key:
            license_rec = self._get_active_license_for_company(company)
            if not license_rec:
                result["reason"] = "no_license"
                return result
        else:
            license_rec = self.env["justech.license"].search(
                [("license_key", "=", key)], limit=1
            )
            if not license_rec:
                return result

        if license_rec.state == "revoked":
            result["reason"] = "revoked"
            return result
        if license_rec.state != "active":
            result["reason"] = "not_active"
            return result
        if license_rec.expires_at and license_rec.expires_at < date.today():
            result["reason"] = "expired"
            result["expires"] = license_rec.expires_at
            return result

        if feature_code:
            feature = self._get_feature_record(feature_code)
            if not feature:
                result["reason"] = "unknown_feature"
                return result
            if feature.license_required:
                granted = license_rec.feature_line_ids.filtered(
                    lambda line: line.feature_id.code == feature_code
                )
                if not granted:
                    result["reason"] = "feature_not_included"
                    result["tier"] = license_rec.tier
                    result["expires"] = license_rec.expires_at or False
                    return result

        result.update(
            {
                "valid": True,
                "reason": "ok",
                "expires": license_rec.expires_at or False,
                "tier": license_rec.tier,
            }
        )
        self._audit(
            "validate",
            license_id=license_rec.id,
            company_id=company.id,
            details={"key": bool(key), "feature_code": feature_code, "result": result},
        )
        return result

    @api.model
    def check_dependencies(self, feature_code, company=None):
        """Return commercial dependency status for a feature."""
        company = company or self.env.company
        feature = self._get_feature_record(feature_code)
        if not feature or not feature.module_id:
            return {"ok": True, "missing": []}

        missing = []
        visited = set()
        self._collect_missing_module_deps(
            feature.module_id, company, missing, visited
        )
        return {"ok": not missing, "missing": missing}

    @api.model
    def activate_feature(self, feature_code, company=None):
        company = company or self.env.company
        feature = self._get_feature_record(feature_code)
        if not feature:
            raise JustechLicenseError(
                _("Unknown feature '%(code)s'.") % {"code": feature_code}
            )
        if feature.always_on:
            return True

        deps = self.check_dependencies(feature_code, company=company)
        if not deps["ok"]:
            missing_codes = ", ".join(item["module_code"] for item in deps["missing"])
            raise JustechLicenseError(
                _("Cannot activate '%(code)s': missing dependencies: %(missing)s.")
                % {"code": feature_code, "missing": missing_codes}
            )

        if feature.license_required:
            if not self._company_has_valid_license(company):
                raise JustechLicenseError(
                    _("No active license for company '%(company)s'.")
                    % {"company": company.name}
                )
            if not self._feature_granted_to_company(feature, company):
                raise JustechLicenseError(
                    _("Feature '%(code)s' is not included in the active license.")
                    % {"code": feature_code}
                )

        self._set_feature_company_active(
            feature, company, active=True, reason="api_activate"
        )
        return True

    @api.model
    def deactivate_feature(self, feature_code, company=None):
        company = company or self.env.company
        feature = self._get_feature_record(feature_code)
        if not feature:
            raise JustechLicenseError(
                _("Unknown feature '%(code)s'.") % {"code": feature_code}
            )
        if feature.always_on:
            raise JustechLicenseError(
                _("Feature '%(code)s' is always-on and cannot be deactivated.")
                % {"code": feature_code}
            )
        self._set_feature_company_active(
            feature, company, active=False, reason="api_deactivate"
        )
        return True

    # ----------------------------------------------------------- registration
    @api.model
    def register_platform_seed(self):
        module = self._upsert_module(
            {
                "code": "justech_modules",
                "name": "Justech Modules",
                "version": "19.0.1.1.0",
                "category": "platform",
                "license_required": False,
                "tier_minimum": "STD",
                "state": "registered",
            }
        )
        self._upsert_feature(
            {
                "code": "platform_core",
                "name": "Platform Core",
                "module_id": module.id,
                "license_required": False,
                "always_on": True,
                "default_active": True,
            }
        )
        ir_module = self.env["ir.module.module"].search(
            [("name", "=", "justech_modules")], limit=1
        )
        if ir_module:
            module.ir_module_id = ir_module.id

    @api.model
    def register_from_manifest(self, module_name, register_data):
        ir_module = self.env["ir.module.module"].search(
            [("name", "=", module_name)], limit=1
        )
        module_vals = {
            "code": register_data.get("code", module_name),
            "name": register_data.get("name") or module_name,
            "version": register_data.get("version"),
            "category": register_data.get("category", "platform"),
            "license_required": register_data.get("license_required", True),
            "tier_minimum": register_data.get("tier_minimum", "STD"),
            "state": "registered",
        }
        module = self._upsert_module(module_vals)
        if ir_module:
            module.ir_module_id = ir_module.id
        feature = self._upsert_feature(
            {
                "code": register_data["feature_code"],
                "name": register_data.get("name") or register_data["feature_code"],
                "module_id": module.id,
                "license_required": register_data.get("license_required", True),
                "always_on": register_data.get("always_on", False),
                "default_active": register_data.get("default_active", False),
            }
        )
        self._audit(
            "register",
            feature_id=feature.id,
            details={"module_name": module_name, "register": register_data},
        )
        return module, feature

    @api.model
    def _set_feature_company_active(
        self, feature, company, active=True, reason="manual"
    ):
        activation = self.env["justech.feature.company"].search(
            [
                ("feature_id", "=", feature.id),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )
        vals = {
            "is_active": active,
            "activated_at": fields.Datetime.now() if active else False,
            "activated_by_id": self.env.uid if active else False,
        }
        if activation:
            activation.write(vals)
        else:
            self.env["justech.feature.company"].create(
                {
                    "feature_id": feature.id,
                    "company_id": company.id,
                    **vals,
                }
            )
        self._audit(
            "activate" if active else "deactivate",
            feature_id=feature.id,
            company_id=company.id,
            details={"reason": reason},
        )

    # -------------------------------------------------------------- internals
    @api.model
    def _get_feature_record(self, feature_code):
        return self.env["justech.feature"].search([("code", "=", feature_code)], limit=1)

    @api.model
    def _company_has_valid_license(self, company):
        return bool(self._get_active_license_for_company(company))

    @api.model
    def _get_active_license_for_company(self, company):
        """Return active license explicitly assigned to company (never global)."""
        today = date.today()
        company_lines = self.env["justech.license.company"].search(
            [
                ("company_id", "=", company.id),
                ("license_id.state", "=", "active"),
            ],
            order="license_id desc",
        )
        for line in company_lines:
            license_rec = line.license_id
            if license_rec.expires_at and license_rec.expires_at < today:
                continue
            return license_rec
        return self.env["justech.license"]

    @api.model
    def _feature_granted_to_company(self, feature, company):
        license_rec = self._get_active_license_for_company(company)
        if not license_rec:
            return False
        if not feature.license_required:
            return True
        return bool(
            license_rec.feature_line_ids.filtered(
                lambda line: line.feature_id.id == feature.id
            )
        )

    @api.model
    def _feature_is_active_for_company(self, feature_id, company_id):
        feature = self.env["justech.feature"].browse(feature_id)
        company = self.env["res.company"].browse(company_id)
        activation = self.env["justech.feature.company"].search(
            [
                ("feature_id", "=", feature.id),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )
        if activation:
            return activation.is_active
        return feature.default_active

    @api.model
    def _order_features_by_module_dependencies(self, features):
        if not features:
            return features
        modules = features.mapped("module_id")
        ordered_modules = self._topological_sort_modules(modules)
        ordered = self.env["justech.feature"]
        for module in ordered_modules:
            ordered |= features.filtered(lambda f, m=module: f.module_id.id == m.id)
        ordered |= features.filtered(lambda f: not f.module_id)
        return ordered

    @api.model
    def _topological_sort_modules(self, modules):
        module_ids = set(modules.ids)
        ordered = self.env["justech.module"]
        remaining = modules
        while remaining:
            progressed = False
            for module in list(remaining):
                required = module.dependency_ids.filtered(
                    lambda dep: dep.dependency_type == "required"
                )
                pending = required.filtered(
                    lambda dep: dep.depends_on_module_id.id in module_ids
                    and dep.depends_on_module_id not in ordered
                )
                if not pending:
                    ordered |= module
                    remaining -= module
                    progressed = True
            if not progressed:
                ordered |= remaining
                break
        return ordered

    @api.model
    def _collect_missing_module_deps(self, module, company, missing, visited):
        if module.id in visited:
            return
        visited.add(module.id)
        for dep in module.dependency_ids.filtered(
            lambda record: record.dependency_type == "required"
        ):
            depends_on = dep.depends_on_module_id
            if not self._module_is_satisfied(depends_on, company):
                missing.append(
                    {
                        "module_code": depends_on.code,
                        "module_name": depends_on.name,
                        "dependency_type": dep.dependency_type,
                    }
                )
            self._collect_missing_module_deps(depends_on, company, missing, visited)

    @api.model
    def _module_is_satisfied(self, module, company):
        if not module.feature_ids:
            return True
        for feature in module.feature_ids:
            if self.is_active(feature.code, company=company):
                return True
        return False

    @api.model
    def _upsert_module(self, vals):
        module = self.env["justech.module"].search([("code", "=", vals["code"])], limit=1)
        if module:
            module.write(vals)
        else:
            module = self.env["justech.module"].create(vals)
        return module

    @api.model
    def _upsert_feature(self, vals):
        feature = self.env["justech.feature"].search(
            [("code", "=", vals["code"])], limit=1
        )
        if feature:
            feature.write(vals)
        else:
            feature = self.env["justech.feature"].create(vals)
        return feature

    @api.model
    def _audit(self, action, feature_id=False, license_id=False, company_id=False, details=None):
        self.env["justech.license.audit"].sudo().create(
            {
                "action": action,
                "feature_id": feature_id,
                "license_id": license_id,
                "company_id": company_id or self.env.company.id,
                "user_id": self.env.uid,
                "details": details or {},
            }
        )
