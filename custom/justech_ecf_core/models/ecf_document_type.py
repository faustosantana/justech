from odoo import fields, models


class JustechEcfDocumentType(models.Model):
    _name = "justech.ecf.document.type"
    _description = "Tipo de comprobante e-CF (catálogo oficial DGII)"
    _order = "code"

    code = fields.Char(required=True, index=True)
    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    xsd_filename = fields.Char(required=True)
    catalog_version = fields.Char(default="1.0", required=True)
    official_modified = fields.Date(string="Modificado en portal DGII")
    notes = fields.Text()

    _sql_constraints = [
        ("code_uniq", "unique(code)", "El código de tipo e-CF debe ser único."),
    ]
