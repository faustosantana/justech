# -*- coding: utf-8 -*-
"""Compat: el wizard vive en justech_l10n_do_ncf; Hellenia solo hereda."""
from odoo import models


class JustechDoNcfVoidWizard(models.TransientModel):
    _inherit = "justech.do.ncf.void.wizard"
