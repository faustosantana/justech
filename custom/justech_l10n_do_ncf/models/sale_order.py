from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    justech_do_document_type_id = fields.Many2one(
        "justech.do.fiscal.document.type",
        string="Tipo de comprobante fiscal",
        domain="[('is_sale_document', '=', True), ('move_type', '=', 'out_invoice')]",
        help="Tipo de comprobante sugerido para la factura de esta cotización.",
    )

    @api.onchange("partner_id")
    def _onchange_partner_justech_do_document_type(self):
        doc = self.partner_id.justech_do_get_default_sale_document_type()
        self.justech_do_document_type_id = doc

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        if self.justech_do_document_type_id:
            invoice_vals["justech_do_document_type_id"] = self.justech_do_document_type_id.id
        return invoice_vals
