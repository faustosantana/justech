from odoo.tests.common import TransactionCase, HttpCase


class TestEcfReceive(TransactionCase):
    def test_receive_duplicate_and_ack(self):
        co = self.env.company
        xml = (
            '<?xml version="1.0" encoding="utf-8"?>'
            "<ECF><Encabezado><Version>1.0</Version>"
            "<IdDoc><TipoeCF>32</TipoeCF><eNCF>E320000000099</eNCF></IdDoc>"
            "<Emisor><RNCEmisor>131880346</RNCEmisor></Emisor>"
            f"<Comprador><RNCComprador>{(co.vat or '000').replace('-','')}</RNCComprador></Comprador>"
            "</Encabezado></ECF>"
        )
        Rec = self.env["justech.ecf.inbound.document"]
        a = Rec.receive_xml(co, xml, auto_draft_invoice=False)
        b = Rec.receive_xml(co, xml, auto_draft_invoice=False)
        self.assertTrue(b.is_duplicate or b.id == a.id)
        self.assertTrue(a.ack_xml)


class TestEcfApiHttp(HttpCase):
    def test_health_and_openapi(self):
        r = self.url_open("/api/v1/ecf/health")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"justech-ecf", r.content)
        r2 = self.url_open("/api/v1/ecf/openapi.json")
        self.assertEqual(r2.status_code, 200)
