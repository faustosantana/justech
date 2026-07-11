# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0.html)
import base64
import html as html_lib
import re
from io import BytesIO

from markupsafe import Markup

from odoo import fields, models
from odoo.tools import html_escape, is_html_empty

DEFAULT_HELLENIA_QUOTATION_TERMS_HTML = """<ul>
<li>Las piezas ofrecidas son únicas y están sujetas a disponibilidad.</li>
<li>Esta cotización tiene una vigencia de cinco (5) días.</li>
<li>Se requiere la confirmación del pago del 100 % para reservar la pieza.</li>
<li>El transporte está disponible previa cotización.</li>
<li>La asesoría de colocación, instalación y styling está disponible previa cotización.</li>
<li>Las piezas pueden presentar marcas propias del tiempo, lo cual forma parte de su carácter y autenticidad.</li>
</ul>"""

# Texto legado (pre-HTML) para detectar y migrar.
_LEGACY_PLAIN_TERMS_PREFIX = "(a) Las piezas ofrecidas son únicas"


class ResCompany(models.Model):
    _inherit = "res.company"

    hellenia_quotation_terms = fields.Html(
        string="Términos y Condiciones (cotizaciones)",
        default=DEFAULT_HELLENIA_QUOTATION_TERMS_HTML,
        sanitize_attributes=True,
        help="Texto precargado en cada cotización nueva. Las cotizaciones existentes conservan su propia copia.",
    )
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

    def get_hellenia_quotation_terms_display(self):
        """Condiciones de cotización con respaldo al texto corporativo por defecto."""
        self.ensure_one()
        if not is_html_empty(self.hellenia_quotation_terms):
            return self.hellenia_quotation_terms
        return Markup(DEFAULT_HELLENIA_QUOTATION_TERMS_HTML)

    @staticmethod
    def hellenia_plain_terms_to_html(terms):
        """Convierte texto plano / HTML escapado a lista HTML profesional."""
        if not terms:
            return False
        text = str(terms).strip()
        if not text:
            return False

        # Deshacer doble escape típico: &lt;br/&gt; visible en UI/PDF.
        if "&lt;" in text:
            text = html_lib.unescape(text)

        # Si ya es HTML con estructura de lista/párrafo, sanitizar y devolver.
        if re.search(r"<(ul|ol|li|p|div|br)\b", text, flags=re.I):
            # Normalizar <br> sueltos dentro de un solo <p> a lista si parece (a)(b)...
            plainish = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
            plainish = re.sub(r"</?p[^>]*>", "\n", plainish, flags=re.I)
            plainish = re.sub(r"<[^>]+>", "", plainish)
            plainish = html_lib.unescape(plainish).strip()
            if re.search(r"^\([a-z]\)\s", plainish, flags=re.I | re.M) or "\n" in plainish:
                text = plainish
            else:
                return Markup(text)

        lines = []
        for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            line = raw.strip()
            if not line:
                continue
            line = re.sub(r"^\([a-z]\)\s*", "", line, flags=re.I)
            line = re.sub(r"^[•\-\*]\s*", "", line)
            if line:
                lines.append(line)
        if not lines:
            return False
        items = "".join(f"<li>{html_escape(line)}</li>" for line in lines)
        return Markup(f'<ul class="jt-hq-terms-list">{items}</ul>')

    def hellenia_get_quotation_terms_html(self):
        """HTML listo para copiar a sale.order.note."""
        self.ensure_one()
        raw = self.hellenia_quotation_terms
        if is_html_empty(raw):
            return Markup(DEFAULT_HELLENIA_QUOTATION_TERMS_HTML)
        converted = self.hellenia_plain_terms_to_html(raw)
        return converted or Markup(DEFAULT_HELLENIA_QUOTATION_TERMS_HTML)

    def hellenia_migrate_quotation_terms_to_html(self):
        """Migra Text legado y aplica redacción corporativa si coincide con el default antiguo."""
        companies = self.sudo().search([])
        for company in companies:
            raw = company.hellenia_quotation_terms
            raw_str = (str(raw) if raw else "").strip()
            if not raw_str or is_html_empty(raw_str):
                company.hellenia_quotation_terms = DEFAULT_HELLENIA_QUOTATION_TERMS_HTML
                continue
            if raw_str.startswith(_LEGACY_PLAIN_TERMS_PREFIX) or raw_str.startswith(
                "<p>(a) Las piezas"
            ) or "&lt;br" in raw_str:
                # Actualizar al texto corporativo elegante (solo si aún es el default legado).
                company.hellenia_quotation_terms = DEFAULT_HELLENIA_QUOTATION_TERMS_HTML
            else:
                converted = company.hellenia_plain_terms_to_html(raw_str)
                if converted:
                    company.hellenia_quotation_terms = converted
        return True

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
