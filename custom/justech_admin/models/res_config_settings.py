# -*- coding: utf-8 -*-
from odoo import models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    def action_justech_open_client_modules(self):
        return self.env["justech.admin.access.service"].action_open_client_modules()

    def action_justech_open_licenses(self):
        return self.env["justech.admin.access.service"].action_open_control_licenses()

    def action_justech_open_security(self):
        return self.env["justech.admin.access.service"].action_open_control_security()

    def action_justech_open_audit(self):
        return self.env["justech.admin.access.service"].action_open_control_audit()
