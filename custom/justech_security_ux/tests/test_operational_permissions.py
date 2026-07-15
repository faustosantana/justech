# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "justech_security_ux")
class TestEnterprisePermissions(TransactionCase):
    def test_fiscal_officer_role_sync(self):
        Users = self.env["res.users"]
        login = "uat_ent_fis_%s" % self.uid
        user = Users.create(
            {
                "name": "UAT Ent Fiscal",
                "login": login,
                "email": "%s@example.com" % login,
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        user.write({"op_role_fiscal": "fiscal_officer"})
        self.assertTrue(
            user.has_group("justech_l10n_do_base.group_justech_do_fiscal_manager")
        )
        self.assertEqual(user.op_role_fiscal, "fiscal_officer")
        self.assertTrue(user.op_act_fis_void)

    def test_finance_apply_action(self):
        Users = self.env["res.users"]
        login = "uat_ent_fin_%s" % self.uid
        user = Users.create(
            {
                "name": "UAT Ent Fin",
                "login": login,
                "email": "%s@example.com" % login,
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        user.write({"op_act_fin_apply": True})
        self.assertTrue(user.has_group("account.group_account_invoice"))
        self.assertTrue(user.op_act_fin_apply)
