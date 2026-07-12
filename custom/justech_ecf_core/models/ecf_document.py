import hashlib

from odoo import api, fields, models, _
from odoo.exceptions import UserError


# Estados alineados al proceso oficial (no inventar estados DGII de respuesta).
ECF_STATES = [
    ("draft", "Borrador"),
    ("validated", "Validado"),
    ("xml_generated", "XML generado"),
    ("signed", "Firmado"),
    ("queued", "En cola"),
    ("sent", "Enviado"),
    ("received_dgii", "Recibido por DGII"),
    ("accepted", "Aceptado"),
    ("rejected", "Rechazado"),
    ("observed", "Observado"),
    ("pending", "Pendiente"),
    ("contingency", "Contingencia"),
    ("retry", "Reintento"),
    ("failed", "Fallido"),
    ("cancelled", "Cancelado"),
]


class JustechEcfDocument(models.Model):
    _name = "justech.ecf.document"
    _description = "Documento electrónico e-CF"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(required=True, default="Nuevo", tracking=True)
    company_id = fields.Many2one("res.company", required=True, index=True, default=lambda s: s.env.company)
    move_id = fields.Many2one("account.move", string="Asiento / factura", index=True, ondelete="restrict")
    document_type_id = fields.Many2one("justech.ecf.document.type", required=True, index=True)
    e_ncf = fields.Char(string="e-NCF", index=True, copy=False)
    state = fields.Selection(ECF_STATES, default="draft", required=True, tracking=True, index=True)
    environment = fields.Selection(
        selection=[
            ("mock", "Simulación"),
            ("testecf", "Pre-certificación"),
            ("certecf", "Certificación"),
            ("ecf", "Producción"),
        ],
        required=True,
        default="mock",
        index=True,
    )
    xml_content = fields.Text(string="XML")
    xml_hash_sha256 = fields.Char(index=True, copy=False)
    signed_xml = fields.Text(string="XML firmado")
    track_id = fields.Char(string="TrackID", index=True, copy=False)
    dgii_status = fields.Char(string="Estado DGII")
    dgii_message = fields.Text(string="Mensaje DGII")
    idempotency_key = fields.Char(index=True, copy=False)
    attempt_count = fields.Integer(default=0)
    contingency = fields.Boolean(default=False)
    event_ids = fields.One2many("justech.ecf.document.event", "document_id", string="Eventos")

    _sql_constraints = [
        (
            "company_encf_uniq",
            "unique(company_id, e_ncf)",
            "El e-NCF debe ser único por empresa.",
        ),
        (
            "idempotency_uniq",
            "unique(company_id, idempotency_key)",
            "La clave de idempotencia debe ser única por empresa.",
        ),
    ]

    def _log_event(self, event_type, result="ok", message=False, payload=False, duration_ms=0):
        self.ensure_one()
        self.env["justech.ecf.document.event"].sudo().create(
            {
                "document_id": self.id,
                "company_id": self.company_id.id,
                "event_type": event_type,
                "result": result,
                "message": message,
                "payload": payload,
                "duration_ms": duration_ms,
                "user_id": self.env.user.id,
                "attempt": self.attempt_count,
            }
        )

    def _set_xml(self, xml_text):
        self.ensure_one()
        digest = hashlib.sha256(xml_text.encode("utf-8")).hexdigest()
        self.write({"xml_content": xml_text, "xml_hash_sha256": digest, "state": "xml_generated"})
        self._log_event("xml_generated", message=_("Hash %s") % digest)

    def action_generate_xml(self):
        for doc in self:
            if "justech.ecf.xml.service" not in self.env:
                raise UserError(_("El módulo XML e-CF no está instalado."))
            xml = self.env["justech.ecf.xml.service"].generate_document_xml(doc)
            doc._set_xml(xml)
        return True

    def action_sign(self):
        for doc in self:
            if "justech.ecf.signature.service" not in self.env:
                raise UserError(_("El módulo de firma e-CF no está instalado."))
            signed = self.env["justech.ecf.signature.service"].sign_document(doc)
            doc.write({"signed_xml": signed, "state": "signed"})
            doc._log_event("signed")
        return True

    def action_enqueue(self):
        for doc in self:
            if doc.state not in ("signed", "retry", "contingency"):
                raise UserError(_("Solo documentos firmados pueden encolarse."))
            if "justech.ecf.queue.job" in self.env:
                self.env["justech.ecf.queue.job"].create_for_document(doc)
            doc.write({"state": "queued"})
            doc._log_event("queued")
        return True

    def action_verify_signature(self):
        self.ensure_one()
        xml = self.signed_xml or self.xml_content
        if not xml:
            from odoo.exceptions import UserError
            raise UserError(_("No hay XML firmado para verificar."))
        res = self.env["justech.ecf.signature.service"].verify_xml_signature(xml)
        self._log_event("verify_signature", result="ok" if res.get("ok") else "error", message=res.get("message"))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Verificación de firma"),
                "message": res.get("message"),
                "type": "success" if res.get("ok") else "danger",
            },
        }

    def action_download_xml(self):

        self.ensure_one()
        content = self.signed_xml or self.xml_content or ""
        if not content:
            raise UserError(_("No hay XML para descargar."))
        attachment = self.env["ir.attachment"].create(
            {
                "name": "%s.xml" % (self.e_ncf or self.name),
                "type": "binary",
                "datas": __import__("base64").b64encode(content.encode("utf-8")),
                "res_model": self._name,
                "res_id": self.id,
                "mimetype": "application/xml",
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }
