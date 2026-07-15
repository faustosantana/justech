# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "justech_security_ux")
class TestOperationalPermissions(TransactionCase):
    def test_pay_apply_maps_to_invoice_group(self):
        Users = self.env["res.users"]
        login = "uat_op_perm_pay_%s" % self.env.cr.dbname
        user = Users.create(
            {
                "name": "UAT Op Perm Pay",
                "login": login,
                "email": "%s@example.com" % login,
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        g_inv = self.env.ref("account.group_account_invoice")
        self.assertFalse(user.op_perm_pay_apply)
        user.write({"op_perm_pay_apply": True})
        self.assertTrue(user.has_group("account.group_account_invoice"))
        self.assertTrue(user.op_perm_pay_apply)
        # Manual group change reflected
        user.write({"group_ids": [(3, g_inv.id)]})
        user.invalidate_recordset()
        self.assertFalse(user.op_perm_pay_apply)

    def test_fiscal_void_maps_to_fiscal_manager(self):
        Users = self.env["res.users"]
        login = "uat_op_perm_fis_%s" % self.env.cr.dbname
        user = Users.create(
            {
                "name": "UAT Op Perm Fiscal",
                "login": login,
                "email": "%s@example.com" % login,
                "group_ids": [(6, 0, [self.env.ref("base.group_user").id])],
            }
        )
        self.assertFalse(user.op_perm_fis_void_ncf)
        user.write({"op_perm_fis_void_ncf": True})
        self.assertTrue(
            user.has_group("justech_l10n_do_base.group_justech_do_fiscal_manager")
        )
