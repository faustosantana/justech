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
        self.assertEqual(action["name"], "Módulos del Cliente")
        control = self.env["justech.client.module.control"].browse(action["res_id"])
        self.assertTrue(control.line_ids)
        self.assertIn("Módulos del Cliente", control.summary_html)
        self.assertTrue(control.license_id or control.client_name)

    def test_client_selector_lists_clients(self):
        clients = self.env["justech.license.service"].get_commercial_clients()
        self.assertTrue(clients)
        self.assertIn("client_name", clients[0])

    def test_administrar_panel_opens(self):
        client = self.env["justech.license.service"].get_commercial_clients()[0]
        control = self.env["justech.client.module.control"].create(
            {
                "license_id": client.get("license_id") or False,
                "company_id": client.get("primary_company_id") or self.env.company.id,
            }
        )
        control._reload_lines()
        self.assertTrue(control.line_ids)
        line = control.line_ids[:1]
        action = line.action_open_administrar()
        self.assertEqual(action["res_model"], "justech.client.module.manage.menu")

    def test_administrar_panel_shows_includes(self):
        client = self.env["justech.license.service"].get_commercial_clients()[0]
        control = self.env["justech.client.module.control"].create(
            {
                "license_id": client.get("license_id") or False,
                "company_id": client.get("primary_company_id") or self.env.company.id,
            }
        )
        control._reload_lines()
        line = control.line_ids.filtered(lambda l: l.main_module_code == "fiscal_rd")[:1]
        self.assertTrue(line)
        self.assertTrue(line.includes)
        menu = self.env["justech.client.module.manage.menu"].create({"line_id": line.id})
        menu._compute_panels()
        self.assertIn("NCF", menu.includes_html)

    def test_development_module_info_only(self):
        client = self.env["justech.license.service"].get_commercial_clients()[0]
        control = self.env["justech.client.module.control"].create(
            {
                "license_id": client.get("license_id") or False,
                "company_id": client.get("primary_company_id") or self.env.company.id,
            }
        )
        control._reload_lines()
        line = control.line_ids.filtered(lambda l: l.section == "development")[:1]
        self.assertTrue(line)
        action = line.action_view_information()
        self.assertEqual(action["res_model"], "justech.client.module.manage.menu")
        menu = self.env["justech.client.module.manage.menu"].create({"line_id": line.id})
        self.assertTrue(menu.is_development)

    def test_activate_opens_key_wizard(self):
        token = self.env["justech.admin.access.service"].issue_critical_grant(
            self.env["justech.admin.access.service"].CRITICAL_PLATFORM_MUTATION
        )
        self.env["justech.license.service"].with_context(
            justech_critical_token=token
        ).execute_client_module_action(
            "mark_paid", "inventario", company=self.env.company
        )
        client = self.env["justech.license.service"].get_commercial_clients()[0]
        control = self.env["justech.client.module.control"].create(
            {
                "license_id": client.get("license_id") or False,
                "company_id": client.get("primary_company_id") or self.env.company.id,
            }
        )
        control._reload_lines()
        line = control.line_ids.filtered(lambda l: l.product_code == "inventario")[:1]
        self.assertTrue(line)
        menu = self.env["justech.client.module.manage.menu"].create({"line_id": line.id})
        action = menu.action_activate()
        self.assertEqual(action["res_model"], "justech.client.module.action.wizard")

    def test_open_without_key_no_popup(self):
        fresh_admin = self.env["res.users"].create(
            {
                "name": "Settings Admin Fresh",
                "login": "settings_admin_f316@hellenia.cloud",
                "group_ids": [(6, 0, [self.env.ref("base.group_system").id])],
            }
        )
        self.env["justech.admin.access"].sudo().ensure_access_shell(
            fresh_admin, company=self.env.company
        )
        action = (
            self.env["justech.admin.access.service"]
            .with_user(fresh_admin)
            .action_open_client_modules()
        )
        self.assertEqual(action["res_model"], "justech.client.module.control")

    def test_filter_active_only(self):
        client = self.env["justech.license.service"].get_commercial_clients()[0]
        control = self.env["justech.client.module.control"].create(
            {
                "license_id": client.get("license_id") or False,
                "company_id": client.get("primary_company_id") or self.env.company.id,
                "filter_mode": "active",
            }
        )
        control._reload_lines()
        self.assertTrue(all(l.is_active for l in control.line_ids))

    def test_audit_has_client_name(self):
        token = self.env["justech.admin.access.service"].issue_critical_grant(
            self.env["justech.admin.access.service"].CRITICAL_PLATFORM_MUTATION
        )
        self.env["justech.license.service"].with_context(
            justech_critical_token=token
        ).execute_client_module_action(
            "mark_paid", "inventario", company=self.env.company
        )
        audit = self.env["justech.client.module.audit"].sudo().search(
            [("product_code", "=", "inventario")], order="id desc", limit=1
        )
        self.assertTrue(audit.client_name)
