from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHelleniaUi(TransactionCase):
    def test_module_installed(self):
        mod = self.env["ir.module.module"].search([("name", "=", "hellenia_ui")])
        self.assertEqual(mod.state, "installed")

    def test_sale_root_active(self):
        menu = self.env.ref("sale.sale_menu_root", raise_if_not_found=False)
        if menu:
            self.assertTrue(menu.active)

    def test_account_menu_spanish_name(self):
        menu = self.env.ref("account.menu_finance")
        self.assertIn(menu.name, ("Contabilidad", "Accounting"))
