import secrets

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class JustechLicense(models.Model):
    _name = "justech.license"
    _description = "Justech License"
    _order = "name"

    name = fields.Char(required=True)
    license_key = fields.Char(required=True, index=True, copy=False)
    tier = fields.Selection(
        [
            ("TRIAL", "Trial"),
            ("STD", "Standard"),
            ("PRO", "Professional"),
            ("ENT", "Enterprise"),
        ],
        required=True,
        default="STD",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("expired", "Expired"),
            ("revoked", "Revoked"),
        ],
        default="draft",
        required=True,
        index=True,
    )
    expires_at = fields.Date()
    max_users = fields.Integer(default=0, help="0 = unlimited")
    max_companies = fields.Integer(default=0, help="0 = unlimited")
    grace_days = fields.Integer(default=7)
    feature_line_ids = fields.One2many(
        "justech.license.feature",
        "license_id",
        string="Licensed Features",
    )
    company_line_ids = fields.One2many(
        "justech.license.company",
        "license_id",
        string="Licensed Companies",
    )
    feature_ids = fields.Many2many(
        "justech.feature",
        compute="_compute_feature_ids",
        string="Features",
    )
    company_ids = fields.Many2many(
        "res.company",
        compute="_compute_company_ids",
        string="Companies",
    )

    _sql_constraints = [
        (
            "license_key_unique",
            "UNIQUE(license_key)",
            "License key must be unique.",
        ),
    ]

    @api.model
    def _generate_license_key(self, tier="STD"):
        token = secrets.token_hex(6).upper()
        return f"JT-{tier}-{token}"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("license_key"):
                vals["license_key"] = self._generate_license_key(
                    vals.get("tier", "STD")
                )
        return super().create(vals_list)

    @api.depends("feature_line_ids.feature_id")
    def _compute_feature_ids(self):
        for license_rec in self:
            license_rec.feature_ids = license_rec.feature_line_ids.feature_id

    @api.depends("company_line_ids.company_id")
    def _compute_company_ids(self):
        for license_rec in self:
            license_rec.company_ids = license_rec.company_line_ids.company_id

    def _check_max_companies(self):
        for license_rec in self:
            if license_rec.max_companies <= 0:
                continue
            count = len(license_rec.company_line_ids)
            if count > license_rec.max_companies:
                raise ValidationError(
                    _(
                        "License '%(name)s' allows at most %(max)s companies "
                        "(%(count)s assigned)."
                    )
                    % {
                        "name": license_rec.name,
                        "max": license_rec.max_companies,
                        "count": count,
                    }
                )

    def action_activate(self):
        for license_rec in self:
            if not license_rec.company_line_ids:
                raise ValidationError(
                    _(
                        "Cannot activate license '%(name)s' without at least "
                        "one assigned company."
                    )
                    % {"name": license_rec.name}
                )
            license_rec._check_max_companies()
            license_rec.state = "active"
            license_rec._sync_company_features()

    def _sync_company_features(self):
        service = self.env["justech.license.service"]
        for license_rec in self:
            if license_rec.state != "active":
                continue
            features = service._order_features_by_module_dependencies(
                license_rec.feature_line_ids.feature_id
            )
            for company_line in license_rec.company_line_ids:
                for feature in features:
                    deps = service.check_dependencies(
                        feature.code,
                        company=company_line.company_id,
                    )
                    if not deps["ok"]:
                        raise ValidationError(
                            _(
                                "Cannot activate feature '%(feature)s' for "
                                "%(company)s: missing dependencies %(missing)s."
                            )
                            % {
                                "feature": feature.code,
                                "company": company_line.company_id.name,
                                "missing": ", ".join(
                                    m["module_code"] for m in deps["missing"]
                                ),
                            }
                        )
                    service.activate_feature(
                        feature.code,
                        company=company_line.company_id,
                    )
