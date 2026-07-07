from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install", "justech_multicurrency")
class TestJustechMulticurrencyAudit(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, justech_audit_skip_license=True))
        cls.audit_installed = "justech.audit.log" in cls.env
        if not cls.audit_installed:
            return
        cls.service = cls.env["justech.audit.service"]
        cls.audit_policy = cls.env["justech.audit.policy"].with_context(active_test=False).search(
            [], limit=1
        )
        if cls.audit_policy:
            cls.audit_policy.write({"active": True})
        cls.policy = cls.env["justech.multicurrency.policy"].get_policy(cls.env.company)
        cls._activate_audit_rule("justech.multicurrency.policy")
        cls._activate_audit_rule("res.currency.rate")
        cls.service._invalidate_runtime_cache()

    @classmethod
    def _activate_audit_rule(cls, model_name):
        model = cls.env["ir.model"].search([("model", "=", model_name)], limit=1)
        if not model:
            return
        rule = cls.env["justech.audit.rule"].sudo().search([("model_id", "=", model.id)], limit=1)
        if rule:
            rule.write({"active": True, "audit_create": True, "audit_write": True})

    def test_audit_rule_registered_if_audit_installed(self):
        if "justech.audit.rule" not in self.env:
            self.skipTest("justech_global_audit_log not installed")
        model = self.env["ir.model"].search([("model", "=", "justech.multicurrency.policy")], limit=1)
        rule = self.env["justech.audit.rule"].search([("model_id", "=", model.id)], limit=1)
        self.assertTrue(rule)

    def test_policy_change_audited(self):
        if not self.audit_installed:
            self.skipTest("justech_global_audit_log not installed")
        before = self.env["justech.audit.log"].search_count(
            [("model_name", "=", "justech.multicurrency.policy"), ("operation_type", "=", "write")]
        )
        self.policy.write({"notes": "MC2 audit test note %s" % before})
        after = self.env["justech.audit.log"].search_count(
            [("model_name", "=", "justech.multicurrency.policy"), ("operation_type", "=", "write")]
        )
        self.assertGreater(after, before)

    def test_rate_change_audited(self):
        if not self.audit_installed:
            self.skipTest("justech_global_audit_log not installed")
        usd = self.env.ref("base.USD")
        usd.active = True
        rate = self.env["res.currency.rate"].create(
            {
                "name": "2026-07-05",
                "currency_id": usd.id,
                "rate": 57.5,
                "justech_rate_origin": "manual",
            }
        )
        before = self.env["justech.audit.log"].search_count(
            [("model_name", "=", "res.currency.rate"), ("operation_type", "=", "write")]
        )
        rate.write({"rate": 57.6})
        after = self.env["justech.audit.log"].search_count(
            [("model_name", "=", "res.currency.rate"), ("operation_type", "=", "write")]
        )
        self.assertGreater(after, before)
