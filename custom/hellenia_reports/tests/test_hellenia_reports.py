# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHelleniaReports(TransactionCase):
    def test_module_installed(self):
        module = self.env["ir.module.module"].search([("name", "=", "hellenia_reports")])
        self.assertTrue(module)
        if module.state == "installed":
            layout = self.env.ref("hellenia_reports.external_layout_hellenia", raise_if_not_found=False)
            self.assertTrue(layout)
            paperformat = self.env.ref("hellenia_reports.paperformat_hellenia_letter", raise_if_not_found=False)
            self.assertTrue(paperformat)
            self.assertEqual(paperformat.format, "Letter")
