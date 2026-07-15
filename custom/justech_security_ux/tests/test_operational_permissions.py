# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "justech_security_ux")
class TestEnterprisePermissions(TransactionCase):
    def _base_user(self, suffix):
        Users = self.env["res.users"]
        login = "uat_ent_%s_%s" % (suffix, self.uid)
        return Users.create(
            {
                "name": "UAT Ent %s" % suffix,
                "login": login,
                "email": "%s@example.com" % login,
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )

    def test_fiscal_officer_role_sync(self):
        user = self._base_user("fis")
        user.write({"op_role_fiscal": "fiscal_officer"})
        self.assertTrue(
            user.has_group("justech_l10n_do_base.group_justech_do_fiscal_manager")
        )
        self.assertEqual(user.op_role_fiscal, "fiscal_officer")
        self.assertTrue(user.op_act_fis_void)
        self.assertTrue(user.op_area_fiscal)

    def test_finance_apply_action(self):
        user = self._base_user("fin")
        user.write({"op_act_fin_apply": True})
        self.assertTrue(user.has_group("account.group_account_invoice"))
        self.assertTrue(user.op_act_fin_apply)

    def test_multiarea_two_independent(self):
        user = self._base_user("multi2")
        user.write(
            {
                "op_area_purchase": True,
                "op_role_purchase": "purchase_user",
                "op_area_commercial": True,
                "op_role_commercial": "commercial_own",
            }
        )
        self.assertTrue(user.op_area_purchase)
        self.assertTrue(user.op_area_commercial)
        self.assertTrue(user.has_group("purchase.group_purchase_user"))
        self.assertTrue(user.has_group("sales_team.group_sale_salesman"))
        # Desactivar solo Compras no toca Comercial
        user.write({"op_area_purchase": False})
        self.assertFalse(user.op_area_purchase)
        self.assertEqual(user.op_role_purchase, "none")
        self.assertFalse(user.has_group("purchase.group_purchase_user"))
        self.assertTrue(user.op_area_commercial)
        self.assertEqual(user.op_role_commercial, "commercial_own")
        self.assertTrue(user.has_group("sales_team.group_sale_salesman"))

    def test_multiarea_three_areas(self):
        user = self._base_user("multi3")
        user.write(
            {
                "op_area_purchase": True,
                "op_role_purchase": "purchase_user",
                "op_area_inventory": True,
                "op_role_inventory": "inventory_user",
                "op_area_fiscal": True,
                "op_role_fiscal": "fiscal_user",
            }
        )
        self.assertTrue(user.op_area_purchase)
        self.assertTrue(user.op_area_inventory)
        self.assertTrue(user.op_area_fiscal)
        self.assertIn("✓", user.op_summary_areas or "")
        self.assertTrue(user.has_group("purchase.group_purchase_user"))
        self.assertTrue(user.has_group("stock.group_stock_user"))
        self.assertTrue(
            user.has_group("justech_l10n_do_base.group_justech_do_fiscal_user")
        )
