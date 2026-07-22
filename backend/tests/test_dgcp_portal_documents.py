"""Tests — descubrimiento de documentos en portal DGCP."""

from __future__ import annotations

from app.services.dgcp_portal_document_service import DGCPPortalDocumentService


SAMPLE_HTML = """
<a onclick="javascript:getAction('/Public/Tendering/OpportunityDetail/DownloadFile' + '?' + 'documentFileId=' + '13021176' + '&mkey=abc',true);">Download</a>
<span>8.DGII-CCC-PEEX-2026-0005 Pliego de Bases de Condiciones.pdf</span>
<a onclick="javascript:getAction('/Public/Tendering/OpportunityDetail/DownloadFile' + '?' + 'documentFileId=' + '13021181' + '&mkey=abc',true);">Download</a>
<span>Anexo. DGII-CCC-PEEX-2026-0005 Borrador de Contrato.pdf</span>
<a onclick="javascript:getAction('/Public/Tendering/OpportunityDetail/DownloadFile' + '?' + 'documentFileId=' + '13021172' + '&mkey=abc',true);">Download</a>
<span>3. DGII-CCC-PEEX-2026-0005 Formulario de Estudios Previos.pdf</span>
"""


def test_discover_from_html_extracts_roles():
    svc = DGCPPortalDocumentService()
    refs = svc.discover_from_html(SAMPLE_HTML, process_code="DGII-CCC-PEEX-2026-0005")
    by_id = {r.portal_document_id: r for r in refs}
    assert "13021176" in by_id
    assert by_id["13021176"].doc_role == "pliego"
    assert by_id["13021181"].doc_role == "anexo"
    assert by_id["13021172"].doc_role == "formulario"


def test_notice_uid_from_url():
    url = "https://comunidad.comprasdominicana.gob.do/Public/Tendering/OpportunityDetail/Index?noticeUID=DO1.NTC.1731126"
    assert DGCPPortalDocumentService.notice_uid_from_url(url) == "DO1.NTC.1731126"


RESIDE_GRID_HTML = """
<tr id="grdGridDocumentList_tr0"><td><span id="tdColumnDocumentNameP2Gen_spnDocumentName_0" class="VortalSpan">Acta de Aprobación de las Bases de la Contratación- MATERIALES DE FERRETERIA-.pdf</span></td><td><span id="spnDocumentTypeSpan_0" class="VortalSpan">Acto de aprobación Especificaciones / Fichas Técnicas / Pliego de Condiciones e Inicio del Procedimiento</span></td><td><a onclick="javascript:getAction('/Public/Tendering/OpportunityDetail/DownloadFile' + '?' + 'documentFileId=' + '12954946' + '&mkey=abc',true);">Download</a></td></tr>
<tr id="grdGridDocumentList_tr1"><td><span id="spnDocumentName_1" class="VortalSpan">FICHA TECNICA-MATERIALES DE FERRETERIA-.pdf</span></td><td><span id="spnDocumentTypeSpan_1" class="VortalSpan">Bases de la Contratación (Especificaciones / Fichas Técnicas / Pliego de Condiciones)</span></td><td><a onclick="javascript:getAction('/Public/Tendering/OpportunityDetail/DownloadFile' + '?' + 'documentFileId=' + '12954948' + '&mkey=abc',true);">Download</a></td></tr>
<tr id="grdGridDocumentList_tr2"><td><span id="spnDocumentName_2" class="VortalSpan">SOLICITUD DE COMPRA O CONTRATACIÓN - MATERIALES DE FERRETERIA-.pdf</span></td><td><span id="spnDocumentTypeSpan_2" class="VortalSpan">Solicitud Compra o Contratación</span></td><td><a onclick="javascript:getAction('/Public/Tendering/OpportunityDetail/DownloadFile' + '?' + 'documentFileId=' + '12954949' + '&mkey=abc',true);">Download</a></td></tr>
"""


def test_discover_reside_without_process_code_in_filename():
    """RESIDE publica títulos sin código del proceso; no deben descartarse."""
    svc = DGCPPortalDocumentService()
    refs = svc.discover_from_html(RESIDE_GRID_HTML, process_code="RESIDE-DAF-CD-2026-0037")
    by_id = {r.portal_document_id: r for r in refs}
    assert len(refs) == 3
    assert by_id["12954946"].doc_role == "pliego"
    assert by_id["12954948"].doc_role == "tdr"
    assert by_id["12954949"].doc_role == "formulario"
