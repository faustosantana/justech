"""Placeholder del dashboard fiscal — Sprint 1 (sin widgets)."""
from odoo import fields, models


class JustechDoFiscalDashboard(models.Model):
    _name = "justech.do.fiscal.dashboard"
    _description = "Justech Fiscal Dashboard Placeholder"
    _rec_name = "company_id"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    note = fields.Text(
        default="Dashboard fiscal Justech — estructura Sprint 1. "
        "Los KPIs y alertas se implementarán en sprints posteriores.",
        readonly=True,
    )
