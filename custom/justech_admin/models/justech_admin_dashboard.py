from odoo import api, fields, models


class JustechAdminDashboard(models.TransientModel):
    _name = "justech.admin.dashboard"
    _description = "Justech Admin Control Center"

    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )
    odoo_version = fields.Char(compute="_compute_summary")
    api_version = fields.Integer(compute="_compute_summary")
    module_count = fields.Integer(compute="_compute_summary")
    active_module_count = fields.Integer(compute="_compute_summary")
    license_count = fields.Integer(compute="_compute_summary")
    feature_count = fields.Integer(compute="_compute_summary")
    role_count = fields.Integer(compute="_compute_summary")
    permission_count = fields.Integer(compute="_compute_summary")
    profile_count = fields.Integer(compute="_compute_summary")
    audit_license_count = fields.Integer(compute="_compute_summary")
    audit_governance_count = fields.Integer(compute="_compute_summary")
    health_status = fields.Char(compute="_compute_summary")
    client_name = fields.Char(compute="_compute_summary")

    @api.depends("company_id")
    def _compute_summary(self):
        license_svc = self.env["justech.license.service"]
        gov_svc = self.env["hellenia.governance.service"]
        for rec in self:
            company = rec.company_id
            catalog = license_svc.get_activation_catalog(company=company)
            active_modules = sum(1 for row in catalog if row.get("is_active"))
            rec.odoo_version = "19.0"
            rec.api_version = license_svc.get_api_version()
            rec.module_count = len(catalog)
            rec.active_module_count = active_modules
            rec.license_count = self.env["justech.license"].search_count(
                [("state", "=", "active")]
            )
            rec.feature_count = self.env["justech.feature"].search_count([])
            rec.role_count = self.env["hellenia.role"].search_count([("active", "=", True)])
            rec.permission_count = self.env["hellenia.permission"].search_count(
                [("active", "=", True)]
            )
            rec.profile_count = self.env["hellenia.user.profile"].search_count(
                [("company_id", "=", company.id), ("active", "=", True)]
            )
            rec.audit_license_count = self.env["justech.license.audit"].search_count([])
            rec.audit_governance_count = self.env["hellenia.governance.audit"].search_count(
                []
            )
            rec.health_status = "OK"
            rec.client_name = company.name

    def action_open_modules(self):
        return self.env.ref("justech_modules.action_justech_module").read()[0]

    def action_open_activation_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Module Activation",
            "res_model": "justech.module.activation.wizard",
            "view_mode": "form",
            "target": "new",
        }

    def action_open_governance_roles(self):
        return self.env.ref("hellenia_governance.action_hellenia_role").read()[0]

    def action_open_governance_permissions(self):
        return self.env.ref("hellenia_governance.action_hellenia_permission").read()[0]

    def action_open_governance_audit(self):
        return self.env.ref("hellenia_governance.action_hellenia_governance_audit").read()[0]

    def action_open_license_audit(self):
        return self.env.ref("justech_modules.action_justech_license_audit").read()[0]
