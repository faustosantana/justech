# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "justech_security_ux")
class TestJustechPermissionsModules(TransactionCase):
    def _user(self, suffix):
        login = "uat_jx_%s_%s" % (suffix, self.uid)
        return self.env["res.users"].create(
            {
                "name": "UAT JX %s" % suffix,
                "login": login,
                "email": "%s@example.com" % login,
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )

    def test_multiarea_persist(self):
        user = self._user("multi")
        user.write(
            {
                "jx_lvl_sales": "all",
                "jx_lvl_purchase": "user",
                "jx_lvl_inventory": "user",
                "jx_lvl_accounting": "invoice",
                "jx_lvl_fiscal": "user",
            }
        )
        self.assertEqual(user.jx_lvl_sales, "all")
        self.assertEqual(user.jx_lvl_purchase, "user")
        self.assertEqual(user.jx_lvl_inventory, "user")
        self.assertEqual(user.jx_lvl_accounting, "invoice")
        self.assertEqual(user.jx_lvl_fiscal, "user")

    def test_isolated_purchase_change(self):
        user = self._user("iso")
        user.write(
            {
                "jx_lvl_sales": "own",
                "jx_lvl_purchase": "user",
                "jx_lvl_inventory": "user",
                "jx_lvl_accounting": "invoice",
                "jx_lvl_fiscal": "officer",
            }
        )
        before = {
            "sales": user.jx_lvl_sales,
            "inv": user.jx_lvl_inventory,
            "acc": user.jx_lvl_accounting,
            "fis": user.jx_lvl_fiscal,
            "sale_g": user.has_group("sales_team.group_sale_salesman"),
            "inv_g": user.has_group("stock.group_stock_user"),
            "fis_g": user.has_group(
                "justech_l10n_do_base.group_justech_do_fiscal_manager"
            ),
        }
        user.write({"jx_lvl_purchase": "manager"})
        self.assertEqual(user.jx_lvl_purchase, "manager")
        self.assertTrue(user.has_group("purchase.group_purchase_manager"))
        self.assertEqual(user.jx_lvl_sales, before["sales"])
        self.assertEqual(user.jx_lvl_inventory, before["inv"])
        self.assertEqual(user.jx_lvl_accounting, before["acc"])
        self.assertEqual(user.jx_lvl_fiscal, before["fis"])
        self.assertEqual(user.has_group("sales_team.group_sale_salesman"), before["sale_g"])
        self.assertEqual(user.has_group("stock.group_stock_user"), before["inv_g"])
        self.assertEqual(
            user.has_group("justech_l10n_do_base.group_justech_do_fiscal_manager"),
            before["fis_g"],
        )

    def test_remove_warranty_keeps_others(self):
        user = self._user("war")
        user.write(
            {
                "jx_lvl_sales": "own",
                "jx_lvl_warranty": "user",
            }
        )
        user.write({"jx_lvl_warranty": "none"})
        self.assertEqual(user.jx_lvl_warranty, "none")
        self.assertFalse(user.has_group("justech_warranty.group_warranty_user"))
        self.assertTrue(user.has_group("sales_team.group_sale_salesman"))

    def test_advanced_manual_group_preserved(self):
        user = self._user("adv")
        portalish = self.env.ref("base.group_partner_manager", raise_if_not_found=False)
        if not portalish:
            self.skipTest("group_partner_manager missing")
        user.write({"group_ids": [(4, portalish.id)]})
        user.write({"jx_lvl_purchase": "user"})
        self.assertTrue(portalish in user.group_ids)
        self.assertTrue(user.has_group("purchase.group_purchase_user"))

    def test_no_implicit_on_empty(self):
        user = self._user("empty")
        self.assertEqual(user.jx_lvl_sales, "none")
        self.assertEqual(user.jx_lvl_purchase, "none")
        self.assertFalse(user.has_group("sales_team.group_sale_salesman"))
        self.assertFalse(user.has_group("purchase.group_purchase_user"))
