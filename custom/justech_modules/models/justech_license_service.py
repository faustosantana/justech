from datetime import date

from odoo import _, api, fields, models
from odoo.tools import ormcache

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
    def clear_license_cache(self):
        """Invalidate cached license lookups (call after license/feature changes)."""
        self.env.registry.clear_cache()

    @api.model
    def is_active(self, feature_code, company=None):
        company = company or self.env.company
        return self._is_active_cached(feature_code, company.id)

    @api.model
    @ormcache("feature_code", "company_id")
    def _is_active_cached(self, feature_code, company_id):
        return self._compute_is_active(feature_code, company_id)

    @api.model
    def _compute_is_active(self, feature_code, company_id):
        company = self.env["res.company"].browse(company_id)
        feature = self._get_feature_record(feature_code)
        if not feature:
            return False
        if feature.always_on:
            return True
        if feature.license_required and not self._feature_granted_to_company(
            feature, company
        ):
            return False
        if not self._feature_is_active_for_company(feature.id, company_id):
            return False
        # LIFE-01: revalidate grant after operational activation flag
        if feature.license_required and not self._feature_granted_to_company(
            feature, company
        ):
            return False
        return True

    @api.model
    def require_active(self, feature_code, company=None):
        if not self.is_active(feature_code, company=company):
            raise JustechLicenseError(
                _("Feature '%(code)s' is not licensed or active for this company.")
                % {"code": feature_code}
            )

    @api.model
    def get_feature(self, feature_code):
        feature_id = self._get_feature_id_cached(feature_code)
        return (
            self.env["justech.feature"].browse(feature_id)
            if feature_id
            else self.env["justech.feature"]
        )

    @api.model
    @ormcache("feature_code")
    def _get_feature_id_cached(self, feature_code):
        feature = self.env["justech.feature"].search(
            [("code", "=", feature_code)], limit=1
        )
        return feature.id or 0

    @api.model
    def validate_license(self, key=None, feature_code=None, company=None):
        company = company or self.env.company
        result = {
            "valid": False,
            "reason": "invalid_key",
            "expires": False,
            "tier": False,
        }
        License = self.env["justech.license"]
        if not key:
            license_rec = self._get_active_license_for_company(company)
            if not license_rec:
                result["reason"] = "no_license"
                return result
        else:
            license_rec = License._find_by_license_key(key)
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
            license_rec = self._get_active_license_for_company(company)
            if not license_rec:
                raise JustechLicenseError(
                    _("No active license for company '%(company)s'.")
                    % {"company": company.name}
                )
            license_rec._check_max_users()
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
                "version": "19.0.1.2.0",
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
        self.clear_license_cache()

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
        self.clear_license_cache()
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
        self.clear_license_cache()

    # -------------------------------------------------------------- internals
    @api.model
    def _get_feature_record(self, feature_code):
        return self.get_feature(feature_code)

    @api.model
    def _company_has_valid_license(self, company):
        return bool(self._get_valid_licenses_for_company(company))

    @api.model
    def _get_valid_licenses_for_company(self, company):
        """All non-expired active licenses explicitly assigned to company."""
        today = date.today()
        company_lines = self.env["justech.license.company"].search(
            [
                ("company_id", "=", company.id),
                ("license_id.state", "=", "active"),
            ]
        )
        valid = self.env["justech.license"]
        for line in company_lines:
            license_rec = line.license_id
            if license_rec.expires_at and license_rec.expires_at < today:
                continue
            valid |= license_rec
        return valid

    @api.model
    def _get_active_license_for_company(self, company):
        """Primary license for company (most recent valid assignment)."""
        valid = self._get_valid_licenses_for_company(company)
        return valid.sorted(key=lambda lic: lic.id, reverse=True)[:1]

    @api.model
    def _feature_granted_to_company(self, feature, company):
        if not feature.license_required:
            return True
        valid_licenses = self._get_valid_licenses_for_company(company)
        if not valid_licenses:
            return False
        for license_rec in valid_licenses:
            if license_rec.feature_line_ids.filtered(
                lambda line: line.feature_id.id == feature.id
            ):
                return True
        return False

    @api.model
    def _feature_is_active_for_company(self, feature_id, company_id):
        activation = self.env["justech.feature.company"].search(
            [
                ("feature_id", "=", feature_id),
                ("company_id", "=", company_id),
            ],
            limit=1,
        )
        if activation:
            return activation.is_active
        feature = self.env["justech.feature"].browse(feature_id)
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
