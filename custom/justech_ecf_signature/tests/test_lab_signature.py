import base64
from pathlib import Path

from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


LAB = Path("/opt/odoo-dev/secrets/ecf-lab")


class TestLabSignature(TransactionCase):
    def _load_lab(self):
        if not (LAB / "lab_valid.p12").exists():
            self.skipTest("Lab P12 not present on this host")
        return (LAB / "lab_valid.p12").read_bytes(), (LAB / "lab_password.txt").read_text().strip()

    def test_sign_and_verify_and_tamper(self):
        p12, password = self._load_lab()
        Sig = self.env["justech.ecf.signature.service"]
        xml = '<?xml version="1.0" encoding="utf-8"?><ECF><Encabezado><Version>1.0</Version></Encabezado></ECF>'
        signed = Sig.sign_xml_bytes(xml.encode(), p12, password)
        self.assertIn("Signature", signed)
        ok = Sig.verify_xml_signature(signed)
        self.assertTrue(ok["ok"], ok)
        tampered = signed.replace("1.0", "9.9", 1)
        bad = Sig.verify_xml_signature(tampered)
        self.assertFalse(bad["ok"])

    def test_corrupt_and_bad_password(self):
        Sig = self.env["justech.ecf.signature.service"]
        xml = b"<ECF/>"
        with self.assertRaises(Exception):
            Sig.sign_xml_bytes(xml, b"NOT-P12", "x")
        p12, _ = self._load_lab()
        with self.assertRaises(Exception):
            Sig.sign_xml_bytes(xml, p12, "wrong-password")
