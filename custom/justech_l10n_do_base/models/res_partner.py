import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError


RNC_RE = re.compile(r"^\d{9,11}$")


class ResPartner(models.Model):
    _inherit = "res.partner"

    justech_do_partner_id_type = fields.Selection(
        selection=[
            ("1", "RNC"),
            ("2", "Cédula"),
            ("3", "Pasaporte"),
        ],
        string="Tipo identificación DGII",
        compute="_compute_justech_do_partner_id_type",
        store=True,
        readonly=False,
        help="Código DGII: 1=RNC (9 dígitos), 2=Cédula (11 dígitos), 3=Pasaporte.",
    )
    justech_do_rnc_valid = fields.Boolean(
        string="RNC Validated",
        compute="_compute_justech_do_rnc_valid",
        store=True,
    )

    @api.depends("vat")
    def _compute_justech_do_partner_id_type(self):
        for partner in self:
            if partner.justech_do_partner_id_type and not partner.vat:
                continue
            cleaned = re.sub(r"[\s\-]", "", partner.vat or "")
            if len(cleaned) == 9:
                partner.justech_do_partner_id_type = "1"
            elif len(cleaned) == 11:
                partner.justech_do_partner_id_type = "2"

    @api.depends("vat", "country_id")
    def _compute_justech_do_rnc_valid(self):
        for partner in self:
            partner.justech_do_rnc_valid = partner._justech_validate_rnc_format(
                partner.vat
            )

    @api.model
    def _justech_validate_rnc_format(self, vat):
        if not vat:
            return False
        cleaned = re.sub(r"[\s\-]", "", vat)
        return bool(RNC_RE.match(cleaned))

    @api.constrains("vat", "country_id")
    def _check_do_rnc_format(self):
        for partner in self:
            if partner.country_id and partner.country_id.code != "DO":
                continue
            if not partner.vat:
                continue
            if not partner._justech_validate_rnc_format(partner.vat):
                raise ValidationError(
                    "Dominican RNC must be 9 to 11 digits (spaces/dashes allowed)."
                )

    def justech_do_has_rnc(self):
        self.ensure_one()
        return bool(self.vat and self._justech_validate_rnc_format(self.vat))

    def justech_do_clean_vat(self):
        """RNC/Cédula sin separadores para exportación DGII."""
        self.ensure_one()
        return re.sub(r"[\s\-]", "", self.vat or "")
