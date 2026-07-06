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
    def _sudo_internal(self):
        """Gatekeeper access to internal licensing models (never use from UI)."""
        from odoo import SUPERUSER_ID

        return self.env(user=SUPERUSER_ID)

    @api.model
    def _require_activation_admin(self):
        """UI/admin mutations require step-up verification (even with session)."""
        if self.env.su or self.env.context.get("justech_skip_critical_step_up"):
            return
        self.env["justech.admin.access.service"].require_critical_step_up(
            self.env["justech.admin.access.service"].CRITICAL_PLATFORM_MUTATION
        )

    @api.model
    def get_feature(self, feature_code):
        feature_id = self._get_feature_id_cached(feature_code)
        return (
            self._sudo_internal()["justech.feature"].browse(feature_id)
            if feature_id
            else self._sudo_internal()["justech.feature"]
        )

    @api.model
    @ormcache("feature_code")
    def _get_feature_id_cached(self, feature_code):
        feature = self._sudo_internal()["justech.feature"].search(
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
        self._require_activation_admin()
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
        self._require_activation_admin()
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
                "version": "19.0.1.5.0",
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
    def register_from_manifest(self, module_name, register_data, manifest=None):
        """Register module catalog entry + features from __manifest__ justech_register."""
        manifest = manifest or {}
        always_enabled = register_data.get("always_enabled", True)
        module_code = (
            register_data.get("module_code")
            or register_data.get("code")
            or module_name
        )
        ir_module = self.env["ir.module.module"].search(
            [("name", "=", module_name)], limit=1
        )
        module_vals = {
            "code": module_code,
            "name": register_data.get("module_name")
            or register_data.get("name")
            or module_name,
            "version": register_data.get("version") or manifest.get("version"),
            "description": register_data.get("description")
            or manifest.get("summary")
            or manifest.get("description"),
            "category": register_data.get("category", "platform"),
            "country": register_data.get("country"),
            "localization": register_data.get("localization"),
            "required_module": register_data.get("required_module", False),
            "license_required": False
            if always_enabled
            else register_data.get("license_required", True),
            "tier_minimum": register_data.get("tier_minimum", "STD"),
            "state": "registered",
        }
        module = self._upsert_module(module_vals)
        if ir_module:
            module.ir_module_id = ir_module.id

        self._register_manifest_dependencies(module, register_data.get("dependencies", []))

        features_data = self._normalize_manifest_features(register_data)
        features = self.env["justech.feature"]
        for feat in features_data:
            feature = self._upsert_feature(
                {
                    "code": feat["code"],
                    "name": feat.get("name") or feat["code"],
                    "description": feat.get("description"),
                    "module_id": module.id,
                    "license_required": False
                    if always_enabled
                    else feat.get("license_required", True),
                    "always_on": feat.get("always_on", False),
                    "default_active": True
                    if always_enabled
                    else feat.get("default_active", False),
                }
            )
            features |= feature

        self._audit(
            "register",
            feature_id=features[:1].id if features else False,
            details={
                "module_name": module_name,
                "module_code": module_code,
                "register": register_data,
            },
        )
        self.clear_license_cache()
        return module, features

    @api.model
    def _normalize_manifest_features(self, register_data):
        if register_data.get("features"):
            return register_data["features"]
        if register_data.get("feature_code"):
            return [
                {
                    "code": register_data["feature_code"],
                    "name": register_data.get("name") or register_data["feature_code"],
                    "description": register_data.get("description"),
                }
            ]
        code = register_data.get("module_code") or register_data.get("code")
        return [{"code": f"{code}_core", "name": register_data.get("module_name") or code}]

    @api.model
    def _register_manifest_dependencies(self, module, dependency_codes):
        Dependency = self.env["justech.module.dependency"]
        Module = self.env["justech.module"]
        for dep_code in dependency_codes:
            depends_on = Module.search([("code", "=", dep_code)], limit=1)
            if not depends_on:
                continue
            existing = Dependency.search(
                [
                    ("module_id", "=", module.id),
                    ("depends_on_module_id", "=", depends_on.id),
                ],
                limit=1,
            )
            if not existing:
                Dependency.create(
                    {
                        "module_id": module.id,
                        "depends_on_module_id": depends_on.id,
                        "dependency_type": "required",
                    }
                )

    # --------------------------------------------------------- activation UI
    @api.model
    def get_activation_catalog(self, company=None):
        """Return module/feature activation rows for admin wizard (API v1)."""
        self.env["justech.admin.access.service"].require_justech_settings_access()
        if not self.env.su:
            self.env["justech.admin.access.service"].require_session(
                self.env["justech.admin.access.service"].SCOPE_PLATFORM
            )
        company = company or self.env.company
        internal = self._sudo_internal()
        catalog = []
        for module in internal["justech.module"].search([], order="category, code"):
            deps = module.dependency_ids.filtered(
                lambda dep: dep.dependency_type == "required"
            )
            feature_rows = []
            module_active = True
            for feature in module.feature_ids:
                activation = internal["justech.feature.company"].search(
                    [
                        ("feature_id", "=", feature.id),
                        ("company_id", "=", company.id),
                    ],
                    limit=1,
                )
                active = self.is_active(feature.code, company=company)
                module_active = module_active and active
                feature_rows.append(
                    {
                        "feature_code": feature.code,
                        "feature_name": feature.name,
                        "description": feature.description,
                        "license_required": feature.license_required,
                        "always_on": feature.always_on,
                        "default_active": feature.default_active,
                        "is_active": active,
                        "activated_at": activation.activated_at,
                        "activated_by_name": activation.activated_by_id.name
                        if activation.activated_by_id
                        else False,
                    }
                )
            catalog.append(
                {
                    "module_code": module.code,
                    "module_name": module.name,
                    "description": module.description,
                    "category": module.category,
                    "country": module.country,
                    "localization": module.localization,
                    "state": module.state,
                    "required_module": module.required_module,
                    "license_required": module.license_required,
                    "dependencies": [
                        {
                            "module_code": dep.depends_on_module_id.code,
                            "module_name": dep.depends_on_module_id.name,
                            "dependency_type": dep.dependency_type,
                        }
                        for dep in deps
                    ],
                    "features": feature_rows,
                    "is_active": module_active if feature_rows else True,
                }
            )
        return catalog

    @api.model
    def get_commercial_catalog(self, company=None):
        """Return commercial product catalog for Control Center (API v1 extension)."""
        self.env["justech.admin.access.service"].require_justech_settings_access()
        if not self.env.su:
            svc = self.env["justech.admin.access.service"]
            if not svc.is_session_valid(svc.SCOPE_ADMIN) and not svc.is_session_valid(
                svc.SCOPE_PLATFORM
            ):
                svc.require_session(svc.SCOPE_ADMIN)
        company = company or self.env.company
        internal = self._sudo_internal()
        Product = internal["justech.commercial.product"]
        tier_labels = dict(Product._fields["license_tier"].selection)
        category_labels = dict(Product._fields["category"].selection)
        catalog = []
        for product in Product.search([("active", "=", True)], order="sequence, name"):
            feature_rows = []
            active_count = 0
            configured_count = 0
            for line in product.line_ids:
                feature = internal["justech.feature"].search(
                    [("code", "=", line.feature_code)], limit=1
                )
                if feature:
                    configured_count += 1
                    active = self.is_active(line.feature_code, company=company)
                    if active:
                        active_count += 1
                    always_on = feature.always_on
                else:
                    active = False
                    always_on = False
                feature_rows.append(
                    {
                        "commercial_name": line.commercial_name,
                        "description": line.description,
                        "feature_code": line.feature_code,
                        "icon": line.icon or "fa-circle",
                        "is_active": active,
                        "always_on": always_on,
                        "configured": bool(feature),
                    }
                )
            if feature_rows:
                if active_count == len(feature_rows):
                    status = "active"
                elif active_count > 0:
                    status = "partial"
                elif configured_count == 0:
                    status = "unavailable"
                else:
                    status = "inactive"
            else:
                status = "unavailable"
            dep_names = []
            for dep_product in Product.search([]):
                if dep_product.id == product.id:
                    continue
                if product.module_map_ids.filtered(
                    lambda m: m.technical_module_code
                    in dep_product.module_map_ids.mapped("technical_module_code")
                ):
                    dep_names.append(dep_product.name)
            catalog.append(
                {
                    "product_code": product.code,
                    "name": product.name,
                    "description": product.description,
                    "icon": product.icon or "fa-cube",
                    "category": product.category,
                    "category_label": category_labels.get(product.category, product.category),
                    "license_tier": product.license_tier,
                    "license_tier_label": tier_labels.get(
                        product.license_tier, product.license_tier
                    ),
                    "version": product.version_display or "—",
                    "status": status,
                    "is_active": status == "active",
                    "features": feature_rows,
                    "dependencies": dep_names,
                    "company_name": company.name,
                }
            )
        return catalog

    @api.model
    def commercial_name_for_feature(self, feature_code):
        """Resolve commercial display name for a technical feature code."""
        internal = self._sudo_internal()
        line = internal["justech.commercial.product.line"].search(
            [("feature_code", "=", feature_code)], limit=1
        )
        if line:
            return line.commercial_name
        feature = internal["justech.feature"].search(
            [("code", "=", feature_code)], limit=1
        )
        return feature.name if feature else feature_code

    # ------------------------------------------------------ client module control
    CLIENT_MODULE_EXCLUDE = ("marketplace", "ia")

    @api.model
    def _client_module_status(self, product, company, state, configured, is_active):
        license_rec = self._get_active_license_for_company(company)
        if license_rec and license_rec.expires_at:
            from datetime import date

            if license_rec.expires_at < date.today():
                return "expired", _("Expirado")
        if not configured:
            return "coming_soon", _("Próximamente")
        if state.is_blocked:
            return "blocked", _("Bloqueado")
        if not state.is_paid:
            return "not_paid", _("No pagado")
        if is_active:
            return "paid_active", _("Pagado y activo")
        return "paid_inactive", _("Pagado pero inactivo")

    @api.model
    def _product_is_active_for_company(self, product, company):
        internal = self._sudo_internal()
        lines = product.line_ids
        if not lines:
            return False
        configured = [
            ln
            for ln in lines
            if internal["justech.feature"].search([("code", "=", ln.feature_code)], limit=1)
        ]
        if not configured:
            return False
        return all(self.is_active(ln.feature_code, company=company) for ln in configured)

    @api.model
    def _product_activation_meta(self, product, company):
        internal = self._sudo_internal()
        activated_at = False
        activated_by = False
        for ln in product.line_ids:
            feat = internal["justech.feature"].search(
                [("code", "=", ln.feature_code)], limit=1
            )
            if not feat:
                continue
            act = internal["justech.feature.company"].search(
                [("feature_id", "=", feat.id), ("company_id", "=", company.id)],
                limit=1,
            )
            if act and act.activated_at:
                if not activated_at or act.activated_at > activated_at:
                    activated_at = act.activated_at
                    activated_by = act.activated_by_id.name if act.activated_by_id else False
        state = internal["justech.client.module.state"].search(
            [("product_id", "=", product.id), ("company_id", "=", company.id)],
            limit=1,
        )
        if state and state.activated_at and (not activated_at or state.activated_at > activated_at):
            activated_at = state.activated_at
            activated_by = state.activated_by_id.name if state.activated_by_id else activated_by
        return activated_at, activated_by

    @api.model
    def _product_last_change_meta(self, product, company):
        Audit = self.env["justech.client.module.audit"].sudo()
        audit = Audit.search(
            [
                ("product_code", "=", product.code),
                ("company_id", "=", company.id),
            ],
            order="create_date desc",
            limit=1,
        )
        if audit:
            user_name = audit.user_id.name if audit.user_id else "—"
            return audit.create_date, user_name
        state = self.env["justech.client.module.state"].sudo().search(
            [("product_id", "=", product.id), ("company_id", "=", company.id)],
            limit=1,
        )
        if state:
            return state.write_date, "—"
        return False, "—"

    @api.model
    def _origin_label(self, origin_code):
        labels = {
            "justech": _("Justech"),
            "marketplace": _("Marketplace"),
            "partner": _("Partner"),
            "client": _("Cliente"),
        }
        return labels.get(origin_code, origin_code or "—")

    @api.model
    def get_client_module_rows(self, company=None, view_only=False):
        """Rows for Módulos del Cliente screen."""
        self.env["justech.admin.access.service"].require_justech_settings_access()
        if not view_only and not self.env.su:
            svc = self.env["justech.admin.access.service"]
            if not svc.is_session_valid(svc.SCOPE_ADMIN):
                svc.require_session(svc.SCOPE_ADMIN)
        company = company or self.env.company
        internal = self._sudo_internal()
        Product = internal["justech.commercial.product"]
        State = internal["justech.client.module.state"]
        license_rec = self._get_active_license_for_company(company)
        tier = license_rec.tier if license_rec else "—"
        rows = []
        for product in Product.search([("active", "=", True)], order="sequence, name"):
            if product.code in self.CLIENT_MODULE_EXCLUDE:
                continue
            configured = any(
                internal["justech.feature"].search(
                    [("code", "=", ln.feature_code)], limit=1
                )
                for ln in product.line_ids
            )
            state = State.get_or_create(product, company)
            is_active = self._product_is_active_for_company(product, company)
            status, status_label = self._client_module_status(
                product, company, state, configured, is_active
            )
            activated_at, activated_by = self._product_activation_meta(product, company)
            last_modified_at, last_modified_by = self._product_last_change_meta(
                product, company
            )
            rows.append(
                {
                    "product_code": product.code,
                    "name": product.name,
                    "description": product.description or "",
                    "is_paid": state.is_paid,
                    "is_active": is_active,
                    "is_blocked": state.is_blocked,
                    "company_name": company.name,
                    "plan_label": tier,
                    "license_label": tier,
                    "activated_at": activated_at,
                    "activated_by_name": activated_by or "—",
                    "last_modified_at": last_modified_at,
                    "last_modified_by_name": last_modified_by or "—",
                    "origin": state.origin or "justech",
                    "origin_label": self._origin_label(state.origin or "justech"),
                    "status": status,
                    "status_label": status_label,
                    "configured": configured,
                    "includes": [ln.commercial_name for ln in product.line_ids],
                }
            )
        return rows

    @api.model
    def _client_module_audit(
        self,
        action,
        product,
        company,
        state_before,
        state_after,
        result="success",
        reason=None,
        details=None,
    ):
        ip = self.env["justech.admin.access.service"]._get_request_ip()
        state = self.env["justech.client.module.state"].sudo().search(
            [("product_id", "=", product.id), ("company_id", "=", company.id)],
            limit=1,
        )
        self.env["justech.client.module.audit"].sudo().create(
            {
                "user_id": self.env.uid,
                "company_id": company.id,
                "ip_address": ip,
                "action": action,
                "origin": state.origin if state else "justech",
                "product_code": product.code,
                "commercial_name": product.name,
                "state_before": state_before,
                "state_after": state_after,
                "result": result,
                "reason": reason,
                "details": details or {},
            }
        )

    @api.model
    def execute_client_module_action(
        self, action, product_code, company=None, target_company=None, reason=None
    ):
        self._require_activation_admin()
        self = self.with_context(justech_skip_critical_step_up=True)
        company = company or self.env.company
        internal = self._sudo_internal()
        product = internal["justech.commercial.product"].search(
            [("code", "=", product_code), ("active", "=", True)], limit=1
        )
        if not product:
            raise JustechLicenseError(
                _("Unknown commercial module '%(code)s'.") % {"code": product_code}
            )
        state = internal["justech.client.module.state"].get_or_create(product, company)
        status_before, _status_label = self._client_module_status(
            product,
            company,
            state,
            bool(product.line_ids),
            self._product_is_active_for_company(product, company),
        )

        if action == "mark_paid":
            state.sudo().write({"is_paid": True})
        elif action == "mark_unpaid":
            state.sudo().write({"is_paid": False})
        elif action == "block":
            state.sudo().write({"is_blocked": True})
        elif action == "unblock":
            state.sudo().write({"is_blocked": False})
        elif action == "activate":
            if not state.is_paid:
                self._client_module_audit(
                    action,
                    product,
                    company,
                    status_before,
                    status_before,
                    result="fail",
                    reason="not_paid",
                )
                raise JustechLicenseError(
                    _(
                        "Este módulo no está incluido en la licencia contratada."
                    )
                )
            if state.is_blocked:
                raise JustechLicenseError(_("Este módulo está bloqueado."))
            for ln in product.line_ids:
                feat = internal["justech.feature"].search(
                    [("code", "=", ln.feature_code)], limit=1
                )
                if feat:
                    self.activate_feature(ln.feature_code, company=company)
            state.sudo().write(
                {
                    "activated_at": fields.Datetime.now(),
                    "activated_by_id": self.env.uid,
                }
            )
        elif action == "deactivate":
            for ln in product.line_ids:
                feat = internal["justech.feature"].search(
                    [("code", "=", ln.feature_code)], limit=1
                )
                if feat and not feat.always_on:
                    self.deactivate_feature(ln.feature_code, company=company)
        elif action == "add_company":
            target = target_company or company
            license_rec = self._get_active_license_for_company(company)
            if not license_rec:
                raise JustechLicenseError(
                    _(
                        "La licencia actual no permite habilitar otra empresa."
                    )
                )
            if license_rec.max_companies > 0:
                current = len(license_rec.company_line_ids)
                if target.id not in license_rec.company_line_ids.mapped("company_id").ids:
                    if current >= license_rec.max_companies:
                        self._client_module_audit(
                            action,
                            product,
                            target,
                            status_before,
                            status_before,
                            result="fail",
                            reason="max_companies",
                        )
                        raise JustechLicenseError(
                            _(
                                "La licencia actual no permite habilitar otra empresa."
                            )
                        )
            if target.id not in license_rec.company_line_ids.mapped("company_id").ids:
                internal["justech.license.company"].create(
                    {"license_id": license_rec.id, "company_id": target.id}
                )
            if state.is_paid:
                for ln in product.line_ids:
                    feat = internal["justech.feature"].search(
                        [("code", "=", ln.feature_code)], limit=1
                    )
                    if feat:
                        self.activate_feature(ln.feature_code, company=target)
        elif action == "remove_company":
            target = target_company
            if not target:
                raise JustechLicenseError(_("Target company required."))
            license_rec = self._get_active_license_for_company(company)
            if license_rec:
                line = license_rec.company_line_ids.filtered(
                    lambda l: l.company_id.id == target.id
                )
                line.unlink()
        else:
            raise JustechLicenseError(_("Unknown action '%(a)s'.") % {"a": action})

        status_after, _status_label = self._client_module_status(
            product,
            company,
            state,
            bool(product.line_ids),
            self._product_is_active_for_company(product, company),
        )
        self._client_module_audit(
            action,
            product,
            company,
            status_before,
            status_after,
            reason=reason,
        )
        return True

    @api.model
    def activate_module(self, module_code, company=None):
        """Activate all features of a commercial module for a company."""
        self._require_activation_admin()
        company = company or self.env.company
        module = self._sudo_internal()["justech.module"].search(
            [("code", "=", module_code)], limit=1
        )
        if not module:
            raise JustechLicenseError(
                _("Unknown module '%(code)s'.") % {"code": module_code}
            )
        for feature in module.feature_ids:
            self.activate_feature(feature.code, company=company)
        return True

    @api.model
    def deactivate_module(self, module_code, company=None):
        """Deactivate all non-always-on features of a module for a company."""
        self._require_activation_admin()
        company = company or self.env.company
        module = self._sudo_internal()["justech.module"].search(
            [("code", "=", module_code)], limit=1
        )
        if not module:
            raise JustechLicenseError(
                _("Unknown module '%(code)s'.") % {"code": module_code}
            )
        for feature in module.feature_ids.filtered(lambda f: not f.always_on):
            self.deactivate_feature(feature.code, company=company)
        return True

    @api.model
    def _set_feature_company_active(
        self, feature, company, active=True, reason="manual"
    ):
        activation = self._sudo_internal()["justech.feature.company"].search(
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
        FeatureCompany = self._sudo_internal()["justech.feature.company"]
        if activation:
            activation.write(vals)
        else:
            FeatureCompany.create(
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
        company_lines = self._sudo_internal()["justech.license.company"].search(
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
        activation = self._sudo_internal()["justech.feature.company"].search(
            [
                ("feature_id", "=", feature_id),
                ("company_id", "=", company_id),
            ],
            limit=1,
        )
        if activation:
            return activation.is_active
        feature = self._sudo_internal()["justech.feature"].browse(feature_id)
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
