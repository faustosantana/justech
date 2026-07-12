"""Firma digital e-CF según documento oficial DGII «Firmado de e-CF».

Algoritmos obligatorios (fuente oficial):
- CanonicalizationMethod: http://www.w3.org/TR/2001/REC-xml-c14n-20010315
- SignatureMethod: http://www.w3.org/2001/04/xmldsig-more#rsa-sha256
- DigestMethod: http://www.w3.org/2001/04/xmlenc#sha256
- Reference URI="" · Transform enveloped-signature · KeyInfo/X509Certificate

Laboratorio: certificado autogenerado NO certifica cumplimiento DGII.
Runtime: cryptography 41 + signxml 3.2 + pyOpenSSL (compatible Odoo 19 servidor).
"""

from odoo import api, models, _
from odoo.exceptions import UserError

C14N = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"


class JustechEcfSignatureService(models.AbstractModel):
    _name = "justech.ecf.signature.service"
    _description = "Servicio de firma XMLDSig e-CF"

    @api.model
    def _load_signing_materials(self, p12_bytes, password: str):
        try:
            from cryptography.hazmat.primitives.serialization import Encoding, pkcs12
            from OpenSSL import crypto
        except ImportError as exc:
            raise UserError(_("Dependencias de firma no disponibles: %s") % exc) from exc

        pwd = password.encode("utf-8") if isinstance(password, str) else password
        key, cert, _additional = pkcs12.load_key_and_certificates(p12_bytes, pwd)
        if key is None or cert is None:
            raise UserError(_("No se pudo leer la clave o el certificado del P12/PFX."))
        openssl_cert = crypto.load_certificate(crypto.FILETYPE_PEM, cert.public_bytes(Encoding.PEM))
        return key, openssl_cert, cert

    @api.model
    def sign_xml_bytes(self, xml_bytes, p12_bytes, password: str):
        try:
            from lxml import etree
            from signxml import XMLSigner, methods
        except ImportError as exc:
            raise UserError(_("Dependencias de firma no disponibles (signxml/lxml): %s") % exc) from exc

        key, openssl_cert, _crypto_cert = self._load_signing_materials(p12_bytes, password)
        root = etree.fromstring(xml_bytes)
        signer = XMLSigner(
            method=methods.enveloped,
            signature_algorithm="rsa-sha256",
            digest_algorithm="sha256",
            c14n_algorithm=C14N,
        )
        # signxml 3.2: cryptography key + OpenSSL cert list
        signed = signer.sign(root, key=key, cert=[openssl_cert])
        return etree.tostring(signed, encoding="unicode")

    @api.model
    def verify_xml_signature(self, xml_text, p12_bytes=None, password=None):
        """Validación criptográfica local (no implica aceptación DGII)."""
        try:
            from lxml import etree
            from signxml import XMLVerifier
        except ImportError as exc:
            raise UserError(_("Dependencias de verificación no disponibles: %s") % exc) from exc
        root = etree.fromstring(xml_text.encode("utf-8") if isinstance(xml_text, str) else xml_text)
        kwargs = {}
        if p12_bytes is not None and password is not None:
            _key, openssl_cert, _c = self._load_signing_materials(p12_bytes, password)
            kwargs["x509_cert"] = openssl_cert
        try:
            XMLVerifier().verify(root, **kwargs)
            return {"ok": True, "message": _("Firma criptográficamente válida (laboratorio/local).")}
        except Exception as exc:
            return {"ok": False, "message": str(exc)[:500]}

    @api.model
    def sign_document(self, document, password=None):
        document.ensure_one()
        if not document.xml_content:
            raise UserError(_("Genere el XML antes de firmar."))
        cfg = self.env["justech.ecf.company.config"].search(
            [("company_id", "=", document.company_id.id)], limit=1
        )
        cert = cfg.certificate_id if cfg else False
        if not cert:
            raise UserError(_("Configure un certificado e-CF para la empresa."))
        if not password and cert.password_token:
            try:
                password = cert._fernet().decrypt(cert.password_token.encode("utf-8")).decode("utf-8")
            except Exception as exc:
                raise UserError(_("No se pudo recuperar la contraseña cifrada del certificado.")) from exc
        if not password:
            raise UserError(
                _("La firma requiere la contraseña del certificado (no se almacena en claro).")
            )
        p12 = cert.decrypt_p12()
        return self.sign_xml_bytes(document.xml_content.encode("utf-8"), p12, password)
