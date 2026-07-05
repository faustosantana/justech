from odoo import fields, models


class JustechLicenseFeature(models.Model):
    _name = "justech.license.feature"
    _description = "Feature included in a License"
    _order = "license_id, feature_id"

    license_id = fields.Many2one(
        "justech.license",
        required=True,
        ondelete="cascade",
        index=True,
    )
    feature_id = fields.Many2one(
        "justech.feature",
        required=True,
        ondelete="restrict",
        index=True,
    )

    _sql_constraints = [
        (
            "license_feature_unique",
            "UNIQUE(license_id, feature_id)",
            "Feature already included in this license.",
        ),
    ]
