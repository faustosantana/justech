from odoo import api, fields, models


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
    justech_do_default_document_type_id = fields.Many2one(
        "justech.do.fiscal.document.type",
        string="Tipo de comprobante fiscal predeterminado",
        domain="[('is_sale_document', '=', True), ('move_type', '=', 'out_invoice')]",
        help="Tipo de comprobante sugerido al crear cotizaciones y facturas para este contacto.",
    )

    @api.depends("vat")
    def _compute_justech_do_partner_id_type(self):
        from odoo.addons.justech_l10n_do_base.validators import rnc_format

        for partner in self:
            if partner.justech_do_partner_id_type and not partner.vat:
                continue
            partner.justech_do_partner_id_type = rnc_format.dgii_id_type_from_vat(partner.vat)

    @api.depends("vat", "country_id")
    def _compute_justech_do_rnc_valid(self):
        for partner in self:
            partner.justech_do_rnc_valid = partner._justech_validate_rnc_format(
                partner.vat
            )

    @api.model
    def _justech_validate_rnc_format(self, vat):
        return self.env["justech.do.fiscal.validator.service"].is_valid_rnc_format(vat)

    @api.constrains("vat", "country_id")
    def _check_do_rnc_format(self):
        for partner in self:
            if partner.country_id and partner.country_id.code != "DO":
                continue
            if not partner.vat:
                continue
            self.env["justech.do.fiscal.validator.service"].validate_rnc_format(partner.vat)

    def justech_do_has_rnc(self):
        self.ensure_one()
        return bool(self.vat and self._justech_validate_rnc_format(self.vat))

    def justech_do_clean_vat(self):
        """RNC/Cédula sin separadores para exportación DGII."""
        self.ensure_one()
        return self.env["justech.do.fiscal.validator.service"].normalize_vat(self.vat)

    def justech_do_get_default_sale_document_type(self):
        """Tipo de comprobante de venta configurado en el contacto (out_invoice)."""
        if not self:
            return False
        self.ensure_one()
        doc = self.justech_do_default_document_type_id
        if doc and doc.is_sale_document and doc.move_type == "out_invoice":
            return doc
        return self.env["justech.do.fiscal.document.type"]
