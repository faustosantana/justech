# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from odoo import fields, models


class BaseDocumentLayout(models.TransientModel):
    """Expose campos corporativos Hellenia en el wizard de diseño de documentos.

    Odoo pasa el registro ``base.document.layout`` como ``company`` en la vista
    previa del configurador. ``external_layout_hellenia`` referencia campos
  de ``res.company`` que no existían en el transient, provocando QWebError al
    renderizar ``account.report_invoice_document_preview``.
    """

    _inherit = "base.document.layout"

    hellenia_legal_notice = fields.Html(
        related="company_id.hellenia_legal_notice",
        readonly=False,
    )
    hellenia_social_facebook = fields.Char(
        related="company_id.hellenia_social_facebook",
        readonly=False,
    )
    hellenia_social_instagram = fields.Char(
        related="company_id.hellenia_social_instagram",
        readonly=False,
    )
    hellenia_social_whatsapp = fields.Char(
        related="company_id.hellenia_social_whatsapp",
        readonly=False,
    )
