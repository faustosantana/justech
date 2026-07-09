"""Resolución de tipo de comprobante fiscal — lógica extraída de account.move."""
from odoo import models


class JustechDoNcfDocumentTypeResolverService(models.AbstractModel):
    _name = "justech.do.ncf.document.type.resolver.service"
    _description = "NCF Document Type Resolver Service"

    def resolve_for_move(self, move):
        move.ensure_one()
        if move.justech_do_document_type_id:
            return move.justech_do_document_type_id
        journal = move.journal_id
        if move.move_type == "out_refund":
            return self.env.ref("justech_l10n_do_base.doc_type_b04", raise_if_not_found=False)
        if move.move_type == "out_invoice" and move.debit_origin_id:
            return self.env.ref("justech_l10n_do_base.doc_type_b03", raise_if_not_found=False)
        if move.move_type == "in_refund" and move.reversed_entry_id:
            return move.reversed_entry_id.justech_do_document_type_id
        if move.move_type == "out_invoice":
            partner_default = move.partner_id.justech_do_get_default_sale_document_type()
            if partner_default:
                return partner_default
            if move.partner_id.justech_do_has_rnc():
                return self.env.ref("justech_l10n_do_base.doc_type_b01", raise_if_not_found=False)
            return self.env.ref("justech_l10n_do_base.doc_type_b02", raise_if_not_found=False)
        if move.move_type == "in_invoice" and journal.justech_do_default_document_type_id:
            doc = journal.justech_do_default_document_type_id
            if doc.is_purchase_ncf():
                return doc
        return self.env["justech.do.fiscal.document.type"]

    def doc_supports_auto_ncf(self, move, doc):
        if not doc:
            return False
        if move.move_type in ("out_invoice", "out_refund") and doc.is_sale_ncf():
            return True
        if move.move_type in ("in_invoice", "in_refund") and doc.is_purchase_ncf():
            return True
        return False

    def should_auto_assign_ncf(self, move):
        move.ensure_one()
        config = self.env["justech.do.fiscal.config.service"]
        if not config.is_fiscal_enabled(move.company_id):
            return False
        if not move.journal_id.justech_do_use_ncf:
            return False
        doc = self.resolve_for_move(move)
        if not doc or not doc.auto_assign_on_post:
            return False
        return self.doc_supports_auto_ncf(move, doc)
