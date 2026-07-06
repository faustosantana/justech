from odoo.tests import tagged

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase

from odoo.addons.justech_modules.tests.test_admin_access import _provision_test_key


@tagged("post_install", "-at_install", "justech_modules")
class TestClientModuleControl(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin = cls.env.ref("base.user_admin")
        cls.admin.write(
            {
                "group_ids": [
                    (4, cls.env.ref("justech_modules.group_justech_internal_admin").id)
                ]
            }
        )
        _provision_test_key(cls.env, cls.admin)
        svc = cls.env["justech.admin.access.service"].with_user(cls.admin)
        svc.open_session("TEST-KEY-12345678", scope=svc.SCOPE_ADMIN)
        cls.env = cls.env(user=cls.admin)
        cls.LicenseSvc = cls.env["justech.license.service"]

    def test_client_module_rows_visible(self):
        rows = self.LicenseSvc.get_client_module_rows(company=self.env.company)
        self.assertTrue(rows)
        codes = {r["product_code"] for r in rows}
        self.assertIn("contabilidad_rd", codes)
        self.assertNotIn("marketplace", codes)
        self.assertNotIn("ia", codes)

    def test_client_module_rows_view_only_without_session(self):
        admin = self.env.ref("base.user_admin")
        svc = self.env["justech.admin.access.service"].with_user(admin)
        svc.revoke_all_sessions(scope=svc.SCOPE_ADMIN)
        rows = self.LicenseSvc.with_user(admin).get_client_module_rows(
            company=self.env.company, view_only=True
        )
        self.assertTrue(rows)

    def test_unpaid_module_cannot_activate(self):
        with self.assertRaises(Exception) as ctx:
            token = self.env["justech.admin.access.service"].issue_critical_grant(
                self.env["justech.admin.access.service"].CRITICAL_PLATFORM_MUTATION
            )
            self.LicenseSvc.with_context(justech_critical_token=token).execute_client_module_action(
                "activate", "contabilidad_rd", company=self.env.company
            )
        self.assertIn("no está incluido", str(ctx.exception))

    def test_mark_paid_and_activate_with_key(self):
        token = self.env["justech.admin.access.service"].issue_critical_grant(
            self.env["justech.admin.access.service"].CRITICAL_PLATFORM_MUTATION
        )
        svc = self.LicenseSvc.with_context(justech_critical_token=token)
        svc.execute_client_module_action(
            "mark_paid", "ux_fiscal", company=self.env.company
        )
        token2 = self.env["justech.admin.access.service"].issue_critical_grant(
            self.env["justech.admin.access.service"].CRITICAL_PLATFORM_MUTATION
        )
        self.LicenseSvc.with_context(justech_critical_token=token2).execute_client_module_action(
            "activate", "ux_fiscal", company=self.env.company
        )
        rows = self.LicenseSvc.get_client_module_rows(company=self.env.company)
        ux = next(r for r in rows if r["product_code"] == "ux_fiscal")
        self.assertTrue(ux["is_paid"])
        self.assertTrue(ux["is_active"])

    def test_audit_logged_on_action(self):
        before = self.env["justech.client.module.audit"].sudo().search_count([])
        token = self.env["justech.admin.access.service"].issue_critical_grant(
            self.env["justech.admin.access.service"].CRITICAL_PLATFORM_MUTATION
        )
        self.LicenseSvc.with_context(justech_critical_token=token).execute_client_module_action(
            "mark_paid", "inventario", company=self.env.company
        )
        after = self.env["justech.client.module.audit"].sudo().search_count([])
        self.assertGreater(after, before)

    def test_client_user_denied(self):
        client = self.env["res.users"].create(
            {
                "name": "Client",
                "login": "client_module_test@hellenia.cloud",
                "group_ids": [(6, 0, [])],
            }
        )
        with self.assertRaises(AccessError):
            self.LicenseSvc.with_user(client).get_client_module_rows()
