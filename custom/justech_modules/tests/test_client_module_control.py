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

    def test_client_module_rows_grouped_main_modules(self):
        rows = self.LicenseSvc.get_client_module_rows(company=self.env.company)
        self.assertTrue(rows)
        main_codes = {r["main_module_code"] for r in rows}
        self.assertIn("fiscal_rd", main_codes)
        self.assertIn("contabilidad", main_codes)
        self.assertIn("punto_de_venta", main_codes)
        self.assertIn("reportes_corporativos", main_codes)
        hidden_as_main = main_codes & {
            "comprobantes_fiscales",
            "ux_fiscal",
            "contabilidad_rd",
        }
        self.assertFalse(hidden_as_main)
        available = [r for r in rows if r.get("section") == "available"]
        development = [r for r in rows if r.get("section") == "development"]
        self.assertGreaterEqual(len(available), 5)
        self.assertLessEqual(len(available), 7)
        self.assertGreaterEqual(len(development), 5)
        fiscal = next(r for r in rows if r["main_module_code"] == "fiscal_rd")
        includes = fiscal.get("includes") or []
        for label in ("NCF", "DGII", "ITBIS", "Comprobantes Fiscales", "Experiencia Fiscal"):
            self.assertIn(label, includes)

    def test_client_module_rows_view_only_without_session(self):
        admin = self.env.ref("base.user_admin")
        svc = self.env["justech.admin.access.service"].with_user(admin)
        svc.revoke_all_sessions(scope=svc.SCOPE_ADMIN)
        rows = self.LicenseSvc.with_user(admin).get_client_module_rows(
            company=self.env.company, view_only=True
        )
        self.assertTrue(rows)
        self.assertIn("display_name", rows[0])
        self.assertIn("section", rows[0])
        self.assertIn("includes", rows[0])

    def test_commercial_clients_api(self):
        clients = self.LicenseSvc.get_commercial_clients()
        self.assertTrue(clients)
        self.assertIn("client_name", clients[0])

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
            "mark_paid", "contabilidad_rd", company=self.env.company
        )
        token2 = self.env["justech.admin.access.service"].issue_critical_grant(
            self.env["justech.admin.access.service"].CRITICAL_PLATFORM_MUTATION
        )
        self.LicenseSvc.with_context(justech_critical_token=token2).execute_client_module_action(
            "activate", "contabilidad_rd", company=self.env.company
        )
        rows = self.LicenseSvc.get_client_module_rows(company=self.env.company)
        fiscal = next(r for r in rows if r["main_module_code"] == "fiscal_rd")
        self.assertTrue(fiscal["is_paid"])
        self.assertTrue(fiscal["is_active"])

    def test_development_modules_not_active(self):
        rows = self.LicenseSvc.get_client_module_rows(company=self.env.company)
        dev_rows = [r for r in rows if r.get("section") == "development"]
        self.assertTrue(dev_rows)
        for row in dev_rows:
            self.assertTrue(row.get("is_development"))
            self.assertEqual(row.get("status"), "coming_soon")
            self.assertFalse(row.get("is_active"))

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
