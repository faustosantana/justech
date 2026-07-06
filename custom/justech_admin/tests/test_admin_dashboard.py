from odoo.tests import tagged

from odoo.tests.common import TransactionCase

from odoo.addons.justech_modules.tests.test_admin_access import _provision_test_key


@tagged("post_install", "-at_install")
class TestJustechAdminDashboard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        admin = cls.env.ref("base.user_admin")
        admin.write(
            {
                "group_ids": [
                    (4, cls.env.ref("justech_modules.group_justech_internal_admin").id)
                ]
            }
        )
        _provision_test_key(cls.env, admin)
        svc = cls.env["justech.admin.access.service"].with_user(admin)
        svc.open_session("TEST-KEY-12345678", scope=svc.SCOPE_ADMIN)
        cls.env = cls.env(user=admin)

    def test_dashboard_renders_enterprise_html(self):
        dashboard = self.env["justech.admin.dashboard"].create(
            {"company_id": self.env.company.id}
        )
        self.assertIn("Centro de Control Justech", dashboard.dashboard_html)
        self.assertIn("justech-cc-card", dashboard.dashboard_html)

    def test_module_catalog_opens(self):
        action = self.env["justech.control.module.catalog"].action_open()
        self.assertEqual(action["res_model"], "justech.control.module.catalog")

    def test_module_sheet_for_contabilidad(self):
        sheet_action = self.env["justech.control.module.sheet"].action_open(
            "contabilidad_rd", company=self.env.company
        )
        sheet = self.env["justech.control.module.sheet"].browse(sheet_action["res_id"])
        self.assertEqual(sheet.name, "Contabilidad Dominicana")
        self.assertTrue(sheet.feature_ids)
        names = sheet.feature_ids.mapped("commercial_name")
        self.assertIn("NCF", names)

    def test_toggle_wizard_requires_key(self):
        sheet_action = self.env["justech.control.module.sheet"].action_open(
            "contabilidad_rd", company=self.env.company
        )
        sheet = self.env["justech.control.module.sheet"].browse(sheet_action["res_id"])
        feat = sheet.feature_ids.filtered(lambda f: f.commercial_name == "NCF")[:1]
        action = feat.action_toggle()
        self.assertEqual(action["res_model"], "justech.control.toggle.wizard")
