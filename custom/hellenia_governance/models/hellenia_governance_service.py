from odoo import _, api, fields, models
from odoo.exceptions import AccessError

from ..exceptions import HelleniaGovernanceError


class HelleniaGovernanceService(models.AbstractModel):
    _name = "hellenia.governance.service"
    _description = "Hellenia Governance Public API"

    @api.model
    def has_permission(self, code, user=None, company=None):
        user = user or self.env.user
        company = company or self.env.company
        if user._is_admin() or user.has_group(
            "hellenia_governance.group_governance_manager"
        ):
            return True
        permission = self.env["hellenia.permission"].search(
            [("code", "=", code), ("active", "=", True)], limit=1
        )
        if not permission:
            return False
        profile = self.get_user_profile(user=user, company=company)
        if not profile:
            return False
        if permission in profile.permission_ids:
            return True
        role_perms = profile.role_ids.permission_ids
        return permission in role_perms

    @api.model
    def require_permission(self, code, user=None, company=None):
        if not self.has_permission(code, user=user, company=company):
            raise AccessError(
                _("Missing functional permission '%(code)s'.") % {"code": code}
            )

    @api.model
    def get_user_profile(self, user=None, company=None):
        user = user or self.env.user
        company = company or self.env.company
        return self.env["hellenia.user.profile"].search(
            [
                ("user_id", "=", user.id),
                ("company_id", "=", company.id),
                ("active", "=", True),
            ],
            limit=1,
        )

    @api.model
    def enable_feature(self, feature_code, company=None):
        company = company or self.env.company
        license_svc = self.env["justech.license.service"]
        if not license_svc.is_active(feature_code, company=company):
            raise HelleniaGovernanceError(
                _("Feature '%(code)s' is not licensed for this company.")
                % {"code": feature_code}
            )
        policy = self._get_or_create_feature_policy(feature_code, company)
        policy.write(
            {
                "enabled": True,
                "enabled_at": fields.Datetime.now(),
                "enabled_by_id": self.env.uid,
            }
        )
        self.audit_event(
            "enable_feature",
            model="hellenia.feature.policy",
            res_id=policy.id,
            company=company,
            details={"feature_code": feature_code},
        )
        return True

    @api.model
    def disable_feature(self, feature_code, company=None):
        company = company or self.env.company
        policy = self.env["hellenia.feature.policy"].search(
            [
                ("feature_code", "=", feature_code),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )
        if not policy:
            policy = self._get_or_create_feature_policy(feature_code, company)
        policy.write({"enabled": False, "enabled_at": False, "enabled_by_id": False})
        self.audit_event(
            "disable_feature",
            model="hellenia.feature.policy",
            res_id=policy.id,
            company=company,
            details={"feature_code": feature_code},
        )
        return True

    @api.model
    def is_feature_enabled(self, feature_code, company=None):
        company = company or self.env.company
        license_svc = self.env["justech.license.service"]
        if not license_svc.is_active(feature_code, company=company):
            return False
        policy = self.env["hellenia.feature.policy"].search(
            [
                ("feature_code", "=", feature_code),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )
        return policy.enabled if policy else True

    @api.model
    def audit_event(
        self, action, model=None, res_id=None, company=None, details=None
    ):
        self.env["hellenia.governance.audit"].sudo().create(
            {
                "action": action,
                "model": model,
                "res_id": res_id or 0,
                "company_id": (company or self.env.company).id,
                "details": details or {},
            }
        )

    @api.model
    def _get_or_create_feature_policy(self, feature_code, company):
        Policy = self.env["hellenia.feature.policy"]
        policy = Policy.search(
            [
                ("feature_code", "=", feature_code),
                ("company_id", "=", company.id),
            ],
            limit=1,
        )
        if policy:
            return policy
        feature = self.env["justech.license.service"].get_feature(feature_code)
        name = feature.name if feature else feature_code
        return Policy.create(
            {
                "feature_code": feature_code,
                "name": name,
                "company_id": company.id,
                "enabled": True,
            }
        )

    @api.model
    def _seed_default_policies(self):
        company = self.env.company
        license_svc = self.env["justech.license.service"]
        for module in self.env["justech.module"].search([]):
            for feature in module.feature_ids:
                if not license_svc.is_active(feature.code, company=company):
                    continue
                self._get_or_create_feature_policy(feature.code, company)
