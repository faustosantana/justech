"""Detección de NCF duplicados — delega validación de formato."""
from odoo import _, models
from odoo.exceptions import ValidationError


class JustechDoNcfDuplicateService(models.AbstractModel):
    _name = "justech.do.ncf.duplicate.service"
    _description = "NCF Duplicate Detection Service"

    def validate_manual_ncf(self, move):
        move.ensure_one()
        if not move.justech_do_ncf:
            return
        validator = self.env["justech.do.fiscal.validator.service"]
        ncf = validator.validate_ncf_format(move.justech_do_ncf)
        move.justech_do_ncf = ncf
        prefix, _seq = validator.parse_ncf(ncf)
        if move.justech_do_document_type_id and prefix != move.justech_do_document_type_id.prefix:
            raise ValidationError(_("NCF prefix does not match document type."))
        self.check_duplicate(move, ncf)

    def check_duplicate(self, move, ncf):
        move.ensure_one()
        dup = move.search(
            [
                ("id", "!=", move.id),
                ("company_id", "=", move.company_id.id),
                ("justech_do_ncf", "=", ncf),
                ("state", "=", "posted"),
                ("justech_do_ncf_voided", "=", False),
            ],
            limit=1,
        )
        if dup:
            raise ValidationError(
                _("NCF %(ncf)s is already used on %(move)s.", ncf=ncf, move=dup.name)
            )
