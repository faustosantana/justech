from odoo.tests import tagged

from odoo.tests.common import TransactionCase

from odoo.addons.justech_modules.tests.test_admin_access import _provision_test_key


@tagged("post_install", "-at_install")
class TestClientModuleControlUI(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.settings_admin = cls.env.ref("base.user_admin")
        _provision_test_key(cls.env, cls.settings_admin)
        svc = cls.env["justech.admin.access.service"].with_user(cls.settings_admin)
        svc.open_session("TEST-KEY-12345678", scope=svc.SCOPE_ADMIN)
        cls.env = cls.env(user=cls.settings_admin)

    def test_control_screen_opens(self):
        action = self.env["justech.client.module.control"].action_open()
        self.assertEqual(action["res_model"], "justech.client.module.control")
        self.assertEqual(action["name"], "Centro de Administración Justech")
        control = self.env["justech.client.module.control"].browse(action["res_id"])
        self.assertTrue(control.line_ids)
        self.assertTrue(all(l.name for l in control.line_ids))
        self.assertIn("Centro de Administración Justech", control.summary_html)
        self.assertIn("Plan contratado", control.summary_html)

    def test_manage_menu_opens(self):
        control = self.env["justech.client.module.control"].create(
            {"company_id": self.env.company.id}
        )
        control._reload_lines()
        line = control.line_ids[:1]
        action = line.action_open_manage_menu()
        self.assertEqual(action["res_model"], "justech.client.module.manage.menu")

    def test_view_details_no_key(self):
        control = self.env["justech.client.module.control"].create(
            {"company_id": self.env.company.id}
        )
        control._reload_lines()
        line = control.line_ids[:1]
        action = line.action_view_details()
        self.assertEqual(action["res_model"], "justech.client.module.control")
        refreshed = self.env["justech.client.module.control"].browse(action["res_id"])
        self.assertTrue(refreshed.panel_open)
        self.assertTrue(refreshed.panel_html)

    def test_activate_opens_key_wizard(self):
        token = self.env["justech.admin.access.service"].issue_critical_grant(
            self.env["justech.admin.access.service"].CRITICAL_PLATFORM_MUTATION
        )
        self.env["justech.license.service"].with_context(
            justech_critical_token=token
        ).execute_client_module_action(
            "mark_paid", "inventario", company=self.env.company
        )
        control = self.env["justech.client.module.control"].create(
            {"company_id": self.env.company.id}
        )
        control._reload_lines()
        line = control.line_ids.filtered(lambda l: l.product_code == "inventario")[:1]
        menu = self.env["justech.client.module.manage.menu"].create({"line_id": line.id})
        action = menu.action_activate()
        self.assertEqual(action["res_model"], "justech.client.module.action.wizard")

    def test_filters_pending_only(self):
        control = self.env["justech.client.module.control"].create(
            {
                "company_id": self.env.company.id,
                "filter_pending_only": True,
            }
        )
        control._reload_lines()
        self.assertTrue(all(not l.is_paid for l in control.line_ids))

    def test_open_client_modules_no_popup_without_key(self):
        fresh_admin = self.env["res.users"].create(
            {
                "name": "Settings Admin Fresh",
                "login": "settings_admin_fresh_f315@hellenia.cloud",
                "group_ids": [(6, 0, [self.env.ref("base.group_system").id])],
            }
        )
        self.env["justech.admin.access"].sudo().ensure_access_shell(
            fresh_admin, company=self.env.company
        )
        svc = self.env["justech.admin.access.service"].with_user(fresh_admin)
        action = svc.action_open_client_modules()
        self.assertEqual(action["res_model"], "justech.client.module.control")

    def test_create_admin_key_opens_setup_wizard(self):
        fresh_admin = self.env["res.users"].create(
            {
                "name": "Settings Admin No Key",
                "login": "settings_admin_no_key_f315@hellenia.cloud",
                "group_ids": [(6, 0, [self.env.ref("base.group_system").id])],
            }
        )
        self.env["justech.admin.access"].sudo().ensure_access_shell(
            fresh_admin, company=self.env.company
        )
        control = self.env["justech.client.module.control"].with_user(fresh_admin).create(
            {"company_id": self.env.company.id}
        )
        action = control.action_create_admin_key()
        self.assertEqual(action["res_model"], "justech.admin.key.setup.wizard")

    def test_client_cannot_see_settings_justech(self):
        client = self.env["res.users"].create(
            {
                "name": "Client Menu",
                "login": "client_menu_test_f315@hellenia.cloud",
                "group_ids": [(6, 0, [])],
            }
        )
        system_group = self.env.ref("base.group_system")
        self.assertFalse(client.has_group(system_group))
