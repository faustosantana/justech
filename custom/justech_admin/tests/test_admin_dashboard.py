from odoo.tests import tagged

from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestJustechAdminDashboard(TransactionCase):
    def test_dashboard_computes(self):
        dashboard = self.env["justech.admin.dashboard"].create(
            {"company_id": self.env.company.id}
        )
        self.assertGreaterEqual(dashboard.module_count, 1)
        self.assertEqual(dashboard.api_version, 1)
        self.assertGreaterEqual(dashboard.permission_count, 1)
        self.assertGreaterEqual(dashboard.role_count, 1)
