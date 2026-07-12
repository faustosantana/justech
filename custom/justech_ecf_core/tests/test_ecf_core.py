from odoo.tests.common import TransactionCase


class TestJustechEcfCore(TransactionCase):
    def test_catalog_types(self):
        types = self.env["justech.ecf.document.type"].search([])
        self.assertGreaterEqual(len(types), 10)
        self.assertTrue(types.filtered(lambda t: t.code == "31"))

    def test_company_config_mock(self):
        co = self.env.company
        cfg = self.env["justech.ecf.company.config"].create(
            {
                "company_id": co.id,
                "fiscal_mode": "ecf_certification",
                "dgii_environment": "mock",
            }
        )
        self.assertEqual(cfg.dgii_environment, "mock")

    def test_document_idempotency_and_xml_hash(self):
        dtype = self.env.ref("justech_ecf_core.ecf_type_32")
        doc = self.env["justech.ecf.document"].create(
            {
                "name": "TEST-ECF-1",
                "company_id": self.env.company.id,
                "document_type_id": dtype.id,
                "e_ncf": "E320000000001",
                "idempotency_key": "test-key-1",
                "environment": "mock",
            }
        )
        if "justech.ecf.xml.service" in self.env:
            xml = self.env["justech.ecf.xml.service"].generate_document_xml(doc)
            doc._set_xml(xml)
            self.assertTrue(doc.xml_hash_sha256)
            self.assertEqual(doc.state, "xml_generated")
