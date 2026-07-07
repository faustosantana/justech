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
        control = self.env["justech.client.module.control"].browse(action["res_id"])
        self.assertTrue(control.line_ids)
        self.assertLessEqual(len(control.line_ids), 5)
        self.assertIn("personalizaciones", control.header_html)

    def test_administrar_panel_has_feature_toggles(self):
        control = self.env["justech.client.module.control"].action_open()
        rec = self.env["justech.client.module.control"].browse(control["res_id"])
        line = rec.line_ids.filtered(lambda l: l.main_module_code == "fiscal_rd")[:1]
        self.assertTrue(line)
        action = line.action_open_administrar()
        panel = self.env["justech.client.module.admin.panel"].browse(action["res_id"])
        self.assertTrue(panel.feature_line_ids)
        self.assertIn("B01 Crédito Fiscal", panel.feature_line_ids.mapped("label"))

    def test_activate_opens_key_wizard(self):
        token = self.env["justech.admin.access.service"].issue_critical_grant(
            self.env["justech.admin.access.service"].CRITICAL_PLATFORM_MUTATION
        )
        self.env["justech.license.service"].with_context(
            justech_critical_token=token
        ).execute_client_module_action(
            "mark_paid", "contabilidad_rd", company=self.env.company
        )
        control = self.env["justech.client.module.control"].action_open()
        rec = self.env["justech.client.module.control"].browse(control["res_id"])
        line = rec.line_ids.filtered(lambda l: l.main_module_code == "fiscal_rd")[:1]
        action = line.action_open_administrar()
        panel = self.env["justech.client.module.admin.panel"].browse(action["res_id"])
        wizard_action = panel.action_activate()
        self.assertEqual(wizard_action["res_model"], "justech.client.module.action.wizard")

    def test_no_forbidden_labels_in_view(self):
        view = self.env.ref("justech_admin.view_justech_client_module_control_form")
        arch = view.arch_db or ""
        for label in ("En desarrollo", "CRM", "Marketplace", "Manufactura"):
            self.assertNotIn(label, arch)
