# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
from odoo import fields, models

DEFAULT_JT_QUOTATION_TERMS = """(a) Las piezas ofrecidas son únicas y sujetas a disponibilidad.
(b) Esta cotización tiene una validez de 5 días.
(c) Se requiere confirmación del pago del 100% para reservar la pieza.
(d) Transporte disponible bajo cotización.
(e) Asesoría de colocación, instalación y styling disponible bajo cotización.
(f) Las piezas pueden presentar marcas propias del tiempo, lo cual forma parte de su carácter y autenticidad."""


class ResCompany(models.Model):
    _inherit = "res.company"

    jt_quotation_terms = fields.Text(
        string="Condiciones por defecto (cotizaciones)",
        default=DEFAULT_JT_QUOTATION_TERMS,
        help="Texto copiado al campo Términos y Condiciones de cada cotización nueva.",
    )

    def jt_get_quotation_terms_text(self):
        """Términos por defecto: hellenia_reports si existe, si no jt_quotation_terms."""
        self.ensure_one()
        hr = getattr(self, "hellenia_quotation_terms", None)
        if hr and str(hr).strip():
            return str(hr).strip()
        return (self.jt_quotation_terms or "").strip()
