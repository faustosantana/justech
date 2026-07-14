import base64

from odoo import fields, models, _
from odoo.exceptions import UserError


class JustechEcfCertificate(models.Model):
    _name = "justech.ecf.certificate"
    _description = "Certificado digital e-CF (almacenamiento cifrado)"
    _order = "date_end desc"

    name = fields.Char(required=True)
    company_id = fields.Many2one("res.company", required=True, index=True, ondelete="cascade")
    state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("valid", "Válido"),
            ("expired", "Vencido"),
            ("invalid", "Inválido"),
        ],
        default="draft",
        required=True,
    )
    # Encrypted blob (Fernet over Odoo secret); never store plaintext password.
    p12_encrypted = fields.Binary(string="P12/PFX cifrado", attachment=False)
    p12_filename = fields.Char()
    password_token = fields.Char(
        string="Token de contraseña",
        help="Referencia cifrada; la contraseña en claro no se persiste.",
        groups="justech_ecf_core.group_ecf_responsible",
    )
    subject_cn = fields.Char(string="Emisor (CN)", readonly=True)
    subject_rnc = fields.Char(string="RNC en certificado", readonly=True)
    serial_number = fields.Char(readonly=True)
    date_start = fields.Datetime(readonly=True)
    date_end = fields.Datetime(readonly=True)
    fingerprint_sha256 = fields.Char(readonly=True)
    last_validation_message = fields.Text(readonly=True)
    alert_days_before_expiry = fields.Integer(default=30)

    def _fernet(self):
        from cryptography.fernet import Fernet
        import hashlib as hl

        secret = (
            self.env["ir.config_parameter"].sudo().get_param("database.secret") or ""
        ).strip()
        if not secret:
            raise UserError(
                _(
                    "No se puede cifrar/descifrar el certificado: falta "
                    "database.secret en el sistema."
                )
            )
        key = base64.urlsafe_b64encode(hl.sha256(secret.encode()).digest())
        return Fernet(key)

    def encrypt_p12(self, raw_bytes):
        self.ensure_one()
        token = self._fernet().encrypt(raw_bytes)
        self.p12_encrypted = base64.b64encode(token)

    def decrypt_p12(self):
        self.ensure_one()
        if not self.p12_encrypted:
            raise UserError(_("No hay certificado cargado."))
        token = base64.b64decode(self.p12_encrypted)
        return self._fernet().decrypt(token)

    def action_validate_certificate(self):
        """Valida P12 sin guardar la contraseña en texto plano."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Validar certificado"),
            "res_model": "justech.ecf.certificate.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_certificate_id": self.id, "default_company_id": self.company_id.id},
        }
