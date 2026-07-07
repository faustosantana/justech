from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


def _provision_admin_key(env, user, plain_key="PERMISSIONS-UX-KEY-4242"):
    access = env["justech.admin.access"].sudo().ensure_access_shell(
        user, company=env.company, access_level="owner"
    )
    access.set_key_hash(plain_key)
    return plain_key


@tagged("post_install", "-at_install", "hellenia_governance")
class TestPermissionsUx(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.registry_items = cls.env["res.users"]._permissions_ux_registry()
        cls.admin = cls.env.ref("base.user_admin")
        cls.plain_key = _provision_admin_key(cls.env, cls.admin)
        cls.test_user = cls.env["res.users"].create(
            {
                "name": "Permissions UX Tester",
                "login": "permissions_ux_test@hellenia.cloud",
                "group_ids": [(6, 0, [])],
            }
        )
        cls.justech_admin_group = cls.env.ref("justech_admin.group_justech_admin_user")
        cls.justech_platform_group = cls.env.ref(
            "justech_modules.group_justech_license_user"
        )

    def test_registry_has_ten_permissions(self):
        self.assertEqual(len(self.registry_items), 10)

    def test_normal_permission_toggle_purchase(self):
        user = self.test_user
        user.perm_ux_purchase = "user"
        purchase_user = self.env.ref("purchase.group_purchase_user")
        self.assertIn(purchase_user, user.group_ids)
        user.perm_ux_purchase = "none"
        self.assertNotIn(purchase_user, user.group_ids)

    def test_direct_protected_group_write_blocked(self):
        with self.assertRaises(AccessError):
            self.test_user.write({"group_ids": [(4, self.justech_admin_group.id)]})

    def test_internal_permission_requires_wizard_without_session(self):
        action = self.test_user.with_context(
            permission_code="justech_admin", target_level="on"
        ).action_permissions_ux_activate_internal()
        self.assertEqual(action.get("res_model"), "hellenia.permissions.internal.wizard")

    def test_internal_permission_with_session(self):
        svc = self.env["justech.admin.access.service"].with_user(self.admin)
        svc.open_session(self.plain_key, scope=svc.SCOPE_ADMIN)
        self.test_user.with_user(self.admin).with_context(
            permission_code="justech_admin", target_level="on"
        ).action_permissions_ux_activate_internal()
        self.assertIn(self.justech_admin_group, self.test_user.group_ids)

    def test_internal_permission_wizard_grants_platform(self):
        wizard = self.env["hellenia.permissions.internal.wizard"].with_user(self.admin).create(
            {
                "user_id": self.test_user.id,
                "permission_code": "justech_platform",
                "target_level": "user",
                "admin_key": self.plain_key,
            }
        )
        wizard.action_confirm()
        self.assertIn(self.justech_platform_group, self.test_user.group_ids)

    def test_session_reuse_skips_wizard(self):
        svc = self.env["justech.admin.access.service"].with_user(self.admin)
        svc.open_session(self.plain_key, scope=svc.SCOPE_ADMIN)
        result = self.test_user.with_user(self.admin).with_context(
            permission_code="justech_platform", target_level="manager"
        ).action_permissions_ux_activate_internal()
        self.assertEqual(result.get("tag"), "reload")
        manager = self.env.ref("justech_modules.group_justech_license_manager")
        self.assertIn(manager, self.test_user.group_ids)
