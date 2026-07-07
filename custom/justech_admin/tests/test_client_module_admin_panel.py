from odoo.tests import tagged

from odoo.exceptions import UserError
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

    def _open_panel_and_line(self, customization_code="fiscal_rd"):
        control = self.env["justech.client.module.control"].action_open()
        rec = self.env["justech.client.module.control"].browse(control["res_id"])
        line = rec.line_ids.filtered(lambda l: l.main_module_code == customization_code)[:1]
        self.assertTrue(line, f"Missing line for {customization_code}")
        panel_action = line.action_open_administrar()
        panel = self.env["justech.client.module.admin.panel"].browse(panel_action["res_id"])
        return rec, line, panel

    def _confirm_wizard(self, panel, line, control, action_type, **extra):
        wizard = self.env["justech.client.module.action.wizard"].create(
            {
                "control_id": control.id,
                "panel_id": panel.id,
                "line_id": line.id,
                "product_code": line.product_code,
                "customization_code": line.main_module_code,
                "action_type": action_type,
                "company_id": control.company_id.id,
                "license_id": control.license_id.id,
                "admin_key": "TEST-KEY-12345678",
                **extra,
            }
        )
        return wizard.action_confirm()

    def test_mark_paid_reopens_panel_after_reload(self):
        control, line, panel = self._open_panel_and_line()
        product_code = line.product_code
        if line.is_paid:
            self._confirm_wizard(panel, line, control, "mark_unpaid")
            control._reload_lines()
            line = control.line_ids.filtered(lambda l: l.product_code == product_code)[:1]
            panel = self.env["justech.client.module.admin.panel"].browse(
                line.action_open_administrar()["res_id"]
            )
        result = self._confirm_wizard(panel, line, control, "mark_paid")
        self.assertEqual(result.get("res_model"), "justech.client.module.admin.panel")
        new_panel = self.env["justech.client.module.admin.panel"].browse(result["res_id"])
        self.assertTrue(new_panel.exists())
        self.assertTrue(new_panel.is_paid)

    def test_add_company_license_limit_is_user_friendly(self):
        control, line, panel = self._open_panel_and_line()
        license_svc = self.env["justech.license.service"]
        license_rec = license_svc._get_active_license_for_company(control.company_id)
        if not license_rec:
            license_rec = license_svc._sudo_internal()["justech.license"].search(
                [("state", "=", "active")], limit=1
            )
        if not license_rec:
            self.skipTest("No active license in test DB")
        license_rec.sudo().write({"max_companies": len(license_rec.company_line_ids)})
        extra_company = self.env["res.company"].search(
            [("id", "not in", license_rec.company_line_ids.mapped("company_id").ids)],
            limit=1,
        )
        self.assertTrue(extra_company)
        wizard = self.env["justech.client.module.action.wizard"].create(
            {
                "control_id": control.id,
                "panel_id": panel.id,
                "line_id": line.id,
                "product_code": line.product_code,
                "customization_code": line.main_module_code,
                "action_type": "add_company",
                "company_id": control.company_id.id,
                "license_id": license_rec.id,
                "target_company_id": extra_company.id,
                "admin_key": "TEST-KEY-12345678",
            }
        )
        with self.assertRaises(UserError) as ctx:
            wizard.action_confirm()
        self.assertIn("no permite habilitar más empresas", str(ctx.exception))
