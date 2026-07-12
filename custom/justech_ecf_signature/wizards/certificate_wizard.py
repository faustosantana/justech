import base64
from datetime import datetime

from odoo import fields, models, _
from odoo.exceptions import UserError


class JustechEcfCertificateWizard(models.TransientModel):
    _name = "justech.ecf.certificate.wizard"
    _description = "Asistente de certificado e-CF"

    company_id = fields.Many2one("res.company", required=True, default=lambda s: s.env.company)
    certificate_id = fields.Many2one("justech.ecf.certificate")
    p12_file = fields.Binary(required=True, string="Archivo P12/PFX")
    p12_filename = fields.Char()
    password = fields.Char(required=True, string="Contraseña del certificado")
    validation_message = fields.Text(readonly=True)
    subject_cn = fields.Char(readonly=True)
    subject_rnc = fields.Char(readonly=True)
    date_end = fields.Datetime(readonly=True)
    state = fields.Selection([("draft", "Borrador"), ("ok", "Válido"), ("error", "Error")], default="draft")

    def action_validate_and_store(self):
        self.ensure_one()
        raw = base64.b64decode(self.p12_file)
        try:
            from cryptography.hazmat.primitives.serialization import pkcs12
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend
        except ImportError as exc:
            raise UserError(_("Falta la librería cryptography: %s") % exc) from exc

        try:
            key, cert, _add = pkcs12.load_key_and_certificates(
                raw, self.password.encode("utf-8"), backend=default_backend()
            )
        except Exception as exc:
            self.write({"state": "error", "validation_message": _("Contraseña incorrecta o archivo corrupto: %s") % exc})
            return self._reopen()

        if cert is None:
            self.write({"state": "error", "validation_message": _("Certificado no encontrado en el archivo.")})
            return self._reopen()

        now = datetime.utcnow()
        expired = cert.not_valid_after.replace(tzinfo=None) < now
        cn = ""
        try:
            cn = cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[0].value
        except Exception:
            cn = str(cert.subject)
        rnc = (self.company_id.vat or "").replace("-", "")
        msg = _("Certificado leído. Emisor: %s. Vigencia hasta %s.") % (cn, cert.not_valid_after)
        if expired:
            msg += " " + _("ATENCIÓN: certificado vencido.")

        Cert = self.env["justech.ecf.certificate"]
        rec = self.certificate_id or Cert.create(
            {"name": self.p12_filename or cn or "Certificado e-CF", "company_id": self.company_id.id}
        )
        rec.encrypt_p12(raw)
        # Store password only as Fernet token, never plaintext field reuse.
        token = rec._fernet().encrypt(self.password.encode("utf-8")).decode("utf-8")
        rec.write(
            {
                "p12_filename": self.p12_filename,
                "password_token": token,
                "subject_cn": cn,
                "subject_rnc": rnc,
                "serial_number": format(cert.serial_number, "x"),
                "date_start": cert.not_valid_before,
                "date_end": cert.not_valid_after,
                "fingerprint_sha256": cert.fingerprint(__import__("hashlib").sha256()).hex(),
                "state": "expired" if expired else "valid",
                "last_validation_message": msg,
            }
        )
        cfg = self.env["justech.ecf.company.config"].search([("company_id", "=", self.company_id.id)], limit=1)
        if not cfg:
            cfg = self.env["justech.ecf.company.config"].create({"company_id": self.company_id.id})
        cfg.certificate_id = rec.id
        self.password = False  # clear from wizard memory
        self.write({"state": "ok", "validation_message": msg, "subject_cn": cn, "date_end": cert.not_valid_after, "certificate_id": rec.id})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"title": _("Certificado almacenado cifrado"), "message": msg, "type": "success", "next": {"type": "ir.actions.act_window_close"}},
        }

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
