from odoo.exceptions import AccessError
from odoo.tests import tagged

from odoo.addons.hellenia_governance.exceptions import HelleniaGovernanceError
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestHelleniaGovernanceService(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.service = cls.env["hellenia.governance.service"]
        cls.company = cls.env.company
        cls.role_cashier = cls.env.ref("hellenia_governance.role_pos_cashier")
        cls.perm_view = cls.env.ref("hellenia_governance.perm_pos_view")
        cls.perm_configure = cls.env.ref("hellenia_governance.perm_pos_configure")
        cls.test_user = cls.env["res.users"].create(
            {
                "name": "Governance Test User",
                "login": "gov_test_user_f312",
                "email": "gov_test_user_f312@test.local",
            }
        )
        cls.env["hellenia.user.profile"].create(
            {
                "user_id": cls.test_user.id,
                "company_id": cls.company.id,
                "role_ids": [(6, 0, [cls.role_cashier.id])],
            }
        )

    def test_has_permission_with_role(self):
        self.assertTrue(
            self.service.has_permission(
                "pos.view", user=self.test_user, company=self.company
            )
        )
        self.assertFalse(
            self.service.has_permission(
                "pos.configure", user=self.test_user, company=self.company
            )
        )

    def test_require_permission_raises(self):
        with self.assertRaises(AccessError):
            self.service.require_permission(
                "pos.configure", user=self.test_user, company=self.company
            )

    def test_enable_feature_requires_license(self):
        with self.assertRaises(HelleniaGovernanceError):
            self.service.enable_feature("nonexistent_feature_xyz", company=self.company)

    def test_enable_disable_feature_licensed(self):
        feature_code = "platform_core"
        self.service.enable_feature(feature_code, company=self.company)
        self.assertTrue(self.service.is_feature_enabled(feature_code))
        self.service.disable_feature(feature_code, company=self.company)
        policy = self.env["hellenia.feature.policy"].search(
            [
                ("feature_code", "=", feature_code),
                ("company_id", "=", self.company.id),
            ],
            limit=1,
        )
        self.assertFalse(policy.enabled)

    def test_audit_event(self):
        before = self.env["hellenia.governance.audit"].search_count([])
        self.service.audit_event("test_action", details={"ok": True})
        self.assertEqual(self.env["hellenia.governance.audit"].search_count([]), before + 1)

    def test_get_user_profile(self):
        profile = self.service.get_user_profile(user=self.test_user, company=self.company)
        self.assertTrue(profile)
        self.assertIn(self.role_cashier, profile.role_ids)
