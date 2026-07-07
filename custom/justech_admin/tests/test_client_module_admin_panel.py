from odoo.tests import tagged

from odoo.tests.common import TransactionCase

from odoo.addons.justech_modules.tests.test_admin_access import _provision_test_key


@tagged("post_install", "-at_install")
class TestClientModuleAdminPanel(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.settings_admin = cls.env.ref("base.user_admin")
        _provision_test_key(cls.env, cls.settings_admin)
        svc = cls.env["justech.admin.access.service"].with_user(cls.settings_admin)
        svc.open_session("TEST-KEY-12345678", scope=svc.SCOPE_ADMIN)
        cls.env = cls.env(user=cls.settings_admin)

    def test_administrar_opens_commercial_panel(self):
        control = self.env["justech.client.module.control"].action_open()
        rec = self.env["justech.client.module.control"].browse(control["res_id"])
        line = rec.line_ids.filtered(lambda l: l.main_module_code == "fiscal_rd")[:1]
        self.assertTrue(line)
        action = line.action_open_administrar()
        self.assertEqual(action["res_model"], "justech.client.module.admin.panel")
        panel = self.env["justech.client.module.admin.panel"].browse(action["res_id"])
        self.assertTrue(panel.feature_line_ids)
        self.assertIn("NCF", panel.feature_line_ids.mapped("label"))
        self.assertTrue(panel.dashboard_header_html)

    def test_fiscal_features_grouped_by_section(self):
        sections = self.env["justech.license.service"].get_commercial_feature_sections(
            "fiscal_rd", company=self.env.company
        )
        labels = [s["section_label"] for s in sections]
        self.assertIn("COMPROBANTES", labels)
        self.assertIn("DGII", labels)
        self.assertIn("IMPUESTOS", labels)
        control = self.env["justech.client.module.control"].action_open()
        rec = self.env["justech.client.module.control"].browse(control["res_id"])
        line = rec.line_ids.filtered(lambda l: l.main_module_code == "fiscal_rd")[:1]
        panel = self.env["justech.client.module.admin.panel"].browse(
            line.action_open_administrar()["res_id"]
        )
        self.assertEqual(
            len(set(panel.feature_line_ids.mapped("section_label"))), len(labels)
        )

    def test_dashboard_view_is_modern_kanban(self):
        view = self.env.ref("justech_admin.view_justech_client_module_admin_panel_form")
        arch = view.arch_db or ""
        self.assertIn("justech-cc-admin-dashboard", arch)
        self.assertIn("justech-dash-feature-kanban", arch)
        self.assertIn("boolean_toggle", arch)
        self.assertNotIn("<list", arch)
        self.assertIn("dashboard_header_html", arch)

    def test_save_features_opens_key_wizard(self):
        control = self.env["justech.client.module.control"].action_open()
        rec = self.env["justech.client.module.control"].browse(control["res_id"])
        line = rec.line_ids.filtered(lambda l: l.main_module_code == "fiscal_rd")[:1]
        panel = self.env["justech.client.module.admin.panel"].browse(
            line.action_open_administrar()["res_id"]
        )
        feature = panel.feature_line_ids.filtered(lambda f: f.feature_key == "ncf")[:1]
        feature.is_active = not feature.initial_active
        save_action = panel.action_save_changes()
        self.assertEqual(save_action["res_model"], "justech.client.module.action.wizard")
        self.assertEqual(save_action["context"]["default_action_type"], "save_features")
