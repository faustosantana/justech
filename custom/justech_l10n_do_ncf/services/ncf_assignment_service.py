"""Asignación de NCF pre-post — orquestación centralizada."""
from odoo import _, fields, models
from odoo.exceptions import UserError


class JustechDoNcfAssignmentService(models.AbstractModel):
    _name = "justech.do.ncf.assignment.service"
    _description = "NCF Assignment Service"

    def assign_before_post(self, moves):
        resolver = self.env["justech.do.ncf.document.type.resolver.service"]
        duplicate = self.env["justech.do.ncf.duplicate.service"]
        rules = self.env["justech.do.ncf.business.rules.service"]
        NcfRange = self.env["justech.do.ncf.range"]

        for move in moves:
            if move.state != "draft":
                continue
            if not self.env["justech.do.fiscal.config.service"].is_fiscal_enabled(move.company_id):
                continue
            if move.justech_do_ncf_voided:
                continue
            doc = resolver.resolve_for_move(move)
            if doc and not move.justech_do_document_type_id:
                move.justech_do_document_type_id = doc.id
            rules.validate_before_post(move)
            if doc and doc.requires_vat and move.move_type in ("out_invoice", "out_refund"):
                if not move.partner_id.justech_do_has_rnc():
                    raise UserError(
                        _(
                            "El tipo de comprobante %(doc)s exige un RNC válido del cliente.",
                            doc=doc.prefix,
                        )
                    )
            if move.justech_do_ncf:
                duplicate.validate_manual_ncf(move)
                continue
            if not resolver.should_auto_assign_ncf(move):
                if move.journal_id.justech_do_use_ncf and move.move_type in (
                    "out_invoice",
                    "out_refund",
                ):
                    raise UserError(
                        _(
                            "Debe indicar o asignar un NCF antes de publicar esta factura."
                        )
                    )
                continue
            doc = move.justech_do_document_type_id
            lock_code = int(doc.code) if doc.code.isdigit() else 0
            self.env.cr.execute(
                "SELECT pg_advisory_xact_lock(%s, %s)",
                [move.company_id.id, lock_code],
            )
            ncf_range = NcfRange._find_active_range_for_update(
                doc, move.journal_id, move.company_id
            )
            if not ncf_range:
                raise UserError(
                    _(
                        "No hay rango NCF activo para el tipo %(prefix)s. "
                        "Revise el Centro de Administración Fiscal.",
                        prefix=doc.prefix,
                    )
                )
            ncf = ncf_range.consume_next(move)
            compat = self.env["justech.do.ncf.compat.sync.service"]
            move.write(compat.assignment_write_vals(move, ncf, ncf_range, doc))
            if move.move_type == "out_refund" and move.reversed_entry_id:
                move.justech_do_origin_ncf = move.reversed_entry_id.justech_do_ncf
            if move.move_type == "in_refund" and move.reversed_entry_id:
                origin_ncf = move.reversed_entry_id.justech_do_ncf
                move.justech_do_origin_ncf = origin_ncf
                if not move.justech_do_ncf_modified:
                    move.justech_do_ncf_modified = origin_ncf

    def moves_for_post(self, moves, soft=True):
        draft = moves.filtered(lambda m: m.state == "draft")
        if soft:
            today = fields.Date.context_today(moves)
            draft = draft.filtered(lambda m: not m.date or m.date <= today)
        return draft
