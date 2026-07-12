import hashlib
from pathlib import Path
from xml.etree import ElementTree as ET

from odoo import api, models, _
from odoo.exceptions import UserError
from odoo.modules.module import get_module_path


class JustechEcfXmlService(models.AbstractModel):
    _name = "justech.ecf.xml.service"
    _description = "Servicio de generación/validación XML e-CF"

    def _xsd_dir(self):
        return Path(get_module_path("justech_ecf_xml")) / "data" / "xsd"

    def get_xsd_path(self, document_type):
        path = self._xsd_dir() / document_type.xsd_filename
        if not path.exists():
            raise UserError(_("XSD oficial no encontrado: %s") % document_type.xsd_filename)
        return path

    @api.model
    def generate_document_xml(self, document):
        """Genera XML mínimo estructural para pruebas (no emisión fiscal real)."""
        document.ensure_one()
        dtype = document.document_type_id
        company = document.company_id
        root = ET.Element("ECF")
        encabezado = ET.SubElement(root, "Encabezado")
        ET.SubElement(encabezado, "Version").text = dtype.catalog_version or "1.0"
        iddoc = ET.SubElement(encabezado, "IdDoc")
        ET.SubElement(iddoc, "TipoeCF").text = dtype.code
        if document.e_ncf:
            ET.SubElement(iddoc, "eNCF").text = document.e_ncf
        emisor = ET.SubElement(encabezado, "Emisor")
        ET.SubElement(emisor, "RNCEmisor").text = (company.vat or "").replace("-", "")
        ET.SubElement(emisor, "RazonSocialEmisor").text = company.name or ""
        xml = ET.tostring(root, encoding="unicode")
        return '<?xml version="1.0" encoding="utf-8"?>\n' + xml

    @api.model
    def validate_against_xsd(self, document):
        document.ensure_one()
        xml = document.signed_xml or document.xml_content
        if not xml:
            raise UserError(_("No hay XML para validar."))
        xsd_path = self.get_xsd_path(document.document_type_id)
        try:
            from lxml import etree
        except ImportError as exc:
            raise UserError(_("lxml es requerido para validación XSD.")) from exc
        schema = etree.XMLSchema(etree.parse(str(xsd_path)))
        doc = etree.fromstring(xml.encode("utf-8"))
        ok = schema.validate(doc)
        errors = "\n".join(str(e) for e in schema.error_log) if not ok else ""
        digest = hashlib.sha256(xml.encode("utf-8")).hexdigest()
        return {"ok": bool(ok), "errors": errors, "sha256": digest, "xsd": xsd_path.name}
