# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
import base64
from io import BytesIO

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    hellenia_primary_color = fields.Char(
        string="Color primario",
        default="#3E4827",
    )
    hellenia_secondary_color = fields.Char(
        string="Color secundario",
        default="#5a6640",
    )
    hellenia_terms_conditions = fields.Html(
        string="Términos y condiciones (documentos)",
    )
    hellenia_legal_notice = fields.Html(
        string="Aviso legal (facturas)",
    )
    hellenia_signature_image = fields.Binary(string="Firma autorizada")
    hellenia_stamp_image = fields.Binary(string="Sello empresa")
    hellenia_social_facebook = fields.Char(string="Facebook")
    hellenia_social_instagram = fields.Char(string="Instagram")
    hellenia_social_whatsapp = fields.Char(string="WhatsApp")
    hellenia_show_qr_on_invoice = fields.Boolean(
        string="Mostrar QR en facturas",
        default=False,
    )

    def hellenia_qr_data_uri(self, value):
        """Genera data-URI PNG para código QR embebido en PDF."""
        self.ensure_one()
        if not value:
            return False
        try:
            import qrcode
        except ImportError:
            return False
        qr = qrcode.make(str(value))
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode()
        return f"data:image/png;base64,{encoded}"
