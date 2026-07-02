# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def hellenia_invoice_qr_uri(self):
        self.ensure_one()
        value = self.justech_do_ncf or self.name
        return self.company_id.hellenia_qr_data_uri(value)

    def hellenia_fiscal_document_title(self):
        """Título fiscal RD para PDF según tipo de comprobante."""
        self.ensure_one()
        doc = self.justech_do_document_type_id
        if doc:
            prefix = (doc.prefix or "").upper()
            mapping = {
                "B01": "FACTURA DE CRÉDITO FISCAL",
                "B02": "FACTURA DE CONSUMO",
                "B03": "NOTA DE DÉBITO",
                "B04": "NOTA DE CRÉDITO",
            }
            if prefix in mapping:
                return mapping[prefix]
            if doc.is_credit_note:
                return "NOTA DE CRÉDITO"
            if getattr(doc, "is_debit_note", False):
                return "NOTA DE DÉBITO"
            return (doc.name or "FACTURA").upper()
        if self.move_type == "out_refund":
            return "NOTA DE CRÉDITO"
        if self.move_type == "in_refund":
            return "NOTA DE CRÉDITO"
        if self.move_type == "out_invoice":
            return "FACTURA"
        if self.move_type == "in_invoice":
            return "FACTURA DE PROVEEDOR"
        return "DOCUMENTO"

    def hellenia_ncf_legal_note(self):
        """Leyenda DGII bajo el NCF."""
        self.ensure_one()
        prefix = ""
        if self.justech_do_document_type_id:
            prefix = (self.justech_do_document_type_id.prefix or "").upper()
        elif self.justech_do_ncf:
            prefix = self.justech_do_ncf[:3].upper()
        if prefix == "B02":
            return "Comprobante de consumo no válido para crédito fiscal."
        if prefix in ("B01", "B03", "B04"):
            return "Válido para crédito fiscal conforme a la DGII."
        return ""

    def hellenia_ncf_type_label(self):
        self.ensure_one()
        if self.justech_do_document_type_id:
            return self.justech_do_document_type_id.name
        return ""
