import hashlib
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class JustechEcfInboundDocument(models.Model):
    _name = "justech.ecf.inbound.document"
    _description = "e-CF recibido de proveedor"
    _order = "id desc"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True, default="Recepción")
    company_id = fields.Many2one("res.company", required=True, index=True)
    state = fields.Selection(
        selection=[
            ("received", "Recibido"),
            ("validated", "Validado"),
            ("rejected", "Rechazado"),
            ("duplicate", "Duplicado"),
            ("draft_linked", "Borrador asociado"),
        ],
        default="received",
        required=True,
        tracking=True,
    )
    xml_content = fields.Text(required=True)
    xml_hash_sha256 = fields.Char(index=True, required=True)
    issuer_rnc = fields.Char(index=True)
    receiver_rnc = fields.Char(index=True)
    e_ncf = fields.Char(index=True)
    document_type_code = fields.Char()
    partner_id = fields.Many2one("res.partner", string="Proveedor")
    is_duplicate = fields.Boolean(default=False)
    signature_ok = fields.Boolean()
    xsd_ok = fields.Boolean()
    xsd_errors = fields.Text()
    differences = fields.Text(string="Diferencias / observaciones")
    draft_move_id = fields.Many2one("account.move", string="Borrador factura", ondelete="set null")
    source = fields.Char(default="manual")
    ack_xml = fields.Text(string="Acuse (ARECF) — borrador local")

    _sql_constraints = [
        (
            "company_hash_uniq",
            "unique(company_id, xml_hash_sha256)",
            "XML duplicado para la empresa.",
        ),
    ]

    @api.model
    def receive_xml(self, company, xml_text, auto_draft_invoice=False, source="manual", token=None):
        if not company:
            raise UserError(_("Empresa requerida."))
        digest = hashlib.sha256(xml_text.encode("utf-8")).hexdigest()
        existing = self.search([("company_id", "=", company.id), ("xml_hash_sha256", "=", digest)], limit=1)
        if existing:
            existing.write({"is_duplicate": True, "state": "duplicate"})
            return existing

        issuer = self._extract_tag(xml_text, "RNCEmisor")
        receiver = self._extract_tag(xml_text, "RNCComprador") or self._extract_tag(xml_text, "RNCReceptor")
        encf = self._extract_tag(xml_text, "eNCF")
        tip = self._extract_tag(xml_text, "TipoeCF")

        # firma
        signature_ok = False
        if "justech.ecf.signature.service" in self.env and "<Signature" in xml_text:
            res = self.env["justech.ecf.signature.service"].verify_xml_signature(xml_text)
            signature_ok = bool(res.get("ok"))

        # XSD best-effort if type known
        xsd_ok = False
        xsd_errors = ""
        dtype = self.env["justech.ecf.document.type"].search([("code", "=", tip)], limit=1) if tip else False
        if dtype and "justech.ecf.xml.service" in self.env:
            tmp = self.env["justech.ecf.document"].new(
                {
                    "company_id": company.id,
                    "document_type_id": dtype.id,
                    "xml_content": xml_text,
                }
            )
            try:
                # validate expects record; use service directly on string via temp write
                from lxml import etree
                from pathlib import Path
                from odoo.modules.module import get_module_path

                xsd_path = Path(get_module_path("justech_ecf_xml")) / "data" / "xsd" / dtype.xsd_filename
                schema = etree.XMLSchema(etree.parse(str(xsd_path)))
                doc = etree.fromstring(xml_text.encode("utf-8"))
                xsd_ok = bool(schema.validate(doc))
                if not xsd_ok:
                    xsd_errors = "\n".join(str(e) for e in schema.error_log)
            except Exception as exc:
                xsd_errors = str(exc)[:500]

        partner = self.env["res.partner"].search(
            [("vat", "ilike", issuer), "|", ("supplier_rank", ">", 0), ("is_company", "=", True)],
            limit=1,
        ) if issuer else self.env["res.partner"]

        company_rnc = (company.vat or "").replace("-", "")
        diffs = []
        if receiver and company_rnc and receiver.replace("-", "") != company_rnc:
            diffs.append(_("RNC receptor (%s) distinto del RNC de la empresa (%s).") % (receiver, company_rnc))
        if not signature_ok:
            diffs.append(_("Firma no válida o ausente (validación local)."))
        if dtype and not xsd_ok:
            diffs.append(_("Validación XSD falló o incompleta."))

        state = "validated" if signature_ok and (xsd_ok or not dtype) and not diffs else "received"
        if diffs and not signature_ok:
            state = "rejected" if not issuer else "received"

        rec = self.create(
            {
                "name": _("Recepción %s") % (encf or digest[:8]),
                "company_id": company.id,
                "xml_content": xml_text,
                "xml_hash_sha256": digest,
                "issuer_rnc": issuer,
                "receiver_rnc": receiver,
                "e_ncf": encf,
                "document_type_code": tip,
                "partner_id": partner.id if partner else False,
                "signature_ok": signature_ok,
                "xsd_ok": xsd_ok,
                "xsd_errors": xsd_errors,
                "differences": "\n".join(diffs),
                "state": state,
                "source": source,
            }
        )

        # Acuse local (ARECF) — estructura mínima; no envío DGII
        rec.ack_xml = (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            "<ARECF><Version>1.0</Version>"
            f"<RNCEmisor>{issuer or ''}</RNCEmisor>"
            f"<eNCF>{encf or ''}</eNCF>"
            f"<Estado>{'0' if state == 'validated' else '1'}</Estado>"
            "<Nota>Acuse local Justech — no enviado a DGII</Nota>"
            "</ARECF>"
        )

        if auto_draft_invoice:
            # Solo con configuración explícita del llamador
            Move = self.env["account.move"]
            move = Move.create(
                {
                    "move_type": "in_invoice",
                    "company_id": company.id,
                    "partner_id": partner.id if partner else False,
                    "ref": encf or digest[:12],
                    "narration": _("Borrador generado desde recepción e-CF (no publicado)."),
                }
            )
            rec.write({"draft_move_id": move.id, "state": "draft_linked"})
        return rec

    @api.model
    def _extract_tag(self, xml_text, tag):
        m = re.search(r"<%s>([^<]+)</%s>" % (re.escape(tag), re.escape(tag)), xml_text)
        return m.group(1).strip() if m else False
