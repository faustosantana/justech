"""API versionada Justech e-CF — /api/v1/ecf

Autenticación: API key en header X-Justech-Api-Key (token hasheado en BD).
Scopes: ecf.read, ecf.write, ecf.receive
Rate limit: por clave / minuto (ICP).
Idempotencia: header Idempotency-Key.
Multiempresa: X-Company-ID o company del token.
No inventa reglas DGII; recepción valida XSD/firma locales.
"""

import hashlib
import json
import logging
import time
from datetime import datetime

from odoo import http, _
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

RATE_BUCKET = {}


def _json(data, status=200):
    return Response(
        json.dumps(data, ensure_ascii=False, default=str),
        status=status,
        mimetype="application/json",
    )


def _error(code, message, status=400, details=None):
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return _json(body, status=status)


class JustechEcfApiController(http.Controller):

    def _authenticate(self, required_scopes=None):
        key = request.httprequest.headers.get("X-Justech-Api-Key")
        if not key:
            return None, _error("auth_required", _("API key requerida."), 401)
        digest = hashlib.sha256(key.encode()).hexdigest()
        Token = request.env["justech.ecf.api.token"].sudo()
        token = Token.search([("key_hash", "=", digest), ("active", "=", True)], limit=1)
        if not token:
            return None, _error("auth_invalid", _("API key inválida."), 401)
        # rate limit
        limit = int(
            request.env["ir.config_parameter"].sudo().get_param("justech_ecf.api_rate_per_minute", "60")
        )
        bucket_key = "%s:%s" % (token.id, int(time.time() // 60))
        RATE_BUCKET[bucket_key] = RATE_BUCKET.get(bucket_key, 0) + 1
        if RATE_BUCKET[bucket_key] > limit:
            return None, _error("rate_limited", _("Límite de solicitudes excedido."), 429)
        scopes = set((token.scopes or "").split(","))
        for sc in required_scopes or []:
            if sc not in scopes and "ecf.admin" not in scopes:
                return None, _error("forbidden", _("Scope insuficiente: %s") % sc, 403)
        company_hdr = request.httprequest.headers.get("X-Company-ID")
        company = False
        if company_hdr:
            company = request.env["res.company"].sudo().browse(int(company_hdr))
            if not company.exists() or company.id not in token.company_ids.ids:
                return None, _error("company_forbidden", _("Empresa no autorizada para este token."), 403)
        else:
            company = token.company_ids[:1]
        return {"token": token, "company": company}, None

    def _audit(self, token, action, company, ok, detail=None):
        request.env["justech.ecf.api.audit"].sudo().create(
            {
                "token_id": token.id if token else False,
                "company_id": company.id if company else False,
                "action": action,
                "success": ok,
                "detail": detail,
                "ip": request.httprequest.remote_addr,
            }
        )

    @http.route("/api/v1/ecf/openapi.json", type="http", auth="public", methods=["GET"], csrf=False)
    def openapi(self, **kwargs):
        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": "Justech e-CF API",
                "version": "1.0.0",
                "description": "API versionada Justech e-CF. No implica certificación DGII.",
            },
            "paths": {
                "/api/v1/ecf/health": {"get": {"summary": "Health"}},
                "/api/v1/ecf/documents": {"get": {"summary": "Listar documentos"}, "post": {"summary": "Crear/encolar"}},
                "/api/v1/ecf/documents/{id}": {"get": {"summary": "Obtener documento"}},
                "/api/v1/ecf/receive": {"post": {"summary": "Recibir e-CF de proveedor"}},
            },
            "components": {
                "securitySchemes": {
                    "ApiKey": {"type": "apiKey", "in": "header", "name": "X-Justech-Api-Key"}
                }
            },
            "security": [{"ApiKey": []}],
        }
        return _json(spec)

    @http.route("/api/v1/ecf/health", type="http", auth="public", methods=["GET"], csrf=False)
    def health(self, **kwargs):
        return _json({"status": "ok", "service": "justech-ecf", "time": datetime.utcnow().isoformat() + "Z"})

    @http.route("/api/v1/ecf/documents", type="http", auth="public", methods=["GET"], csrf=False)
    def list_documents(self, **kwargs):
        auth, err = self._authenticate(["ecf.read"])
        if err:
            return err
        domain = [("company_id", "=", auth["company"].id)]
        docs = request.env["justech.ecf.document"].sudo().search(domain, limit=100, order="id desc")
        self._audit(auth["token"], "list_documents", auth["company"], True)
        return _json(
            {
                "data": [
                    {
                        "id": d.id,
                        "name": d.name,
                        "e_ncf": d.e_ncf,
                        "state": d.state,
                        "track_id": d.track_id,
                        "environment": d.environment,
                    }
                    for d in docs
                ]
            }
        )

    @http.route("/api/v1/ecf/documents/<int:doc_id>", type="http", auth="public", methods=["GET"], csrf=False)
    def get_document(self, doc_id, **kwargs):
        auth, err = self._authenticate(["ecf.read"])
        if err:
            return err
        doc = request.env["justech.ecf.document"].sudo().browse(doc_id)
        if not doc.exists() or doc.company_id.id != auth["company"].id:
            return _error("not_found", _("Documento no encontrado."), 404)
        self._audit(auth["token"], "get_document", auth["company"], True, str(doc_id))
        return _json(
            {
                "data": {
                    "id": doc.id,
                    "name": doc.name,
                    "e_ncf": doc.e_ncf,
                    "state": doc.state,
                    "track_id": doc.track_id,
                    "xml_hash_sha256": doc.xml_hash_sha256,
                    "dgii_status": doc.dgii_status,
                }
            }
        )

    @http.route("/api/v1/ecf/documents", type="http", auth="public", methods=["POST"], csrf=False)
    def create_document(self, **kwargs):
        auth, err = self._authenticate(["ecf.write"])
        if err:
            return err
        try:
            payload = json.loads(request.httprequest.data.decode() or "{}")
        except Exception:
            return _error("invalid_json", _("JSON inválido."))
        idem = request.httprequest.headers.get("Idempotency-Key") or payload.get("idempotency_key")
        Doc = request.env["justech.ecf.document"].sudo()
        if idem:
            existing = Doc.search(
                [("company_id", "=", auth["company"].id), ("idempotency_key", "=", idem)], limit=1
            )
            if existing:
                self._audit(auth["token"], "create_idempotent", auth["company"], True, idem)
                return _json({"data": {"id": existing.id, "state": existing.state, "idempotent": True}})
        dtype_code = payload.get("document_type_code") or "32"
        dtype = request.env["justech.ecf.document.type"].sudo().search([("code", "=", dtype_code)], limit=1)
        if not dtype:
            return _error("invalid_type", _("Tipo e-CF desconocido."))
        doc = Doc.create(
            {
                "name": payload.get("name") or "API-ECF",
                "company_id": auth["company"].id,
                "document_type_id": dtype.id,
                "e_ncf": payload.get("e_ncf"),
                "idempotency_key": idem,
                "environment": payload.get("environment") or "mock",
            }
        )
        self._audit(auth["token"], "create_document", auth["company"], True, str(doc.id))
        return _json({"data": {"id": doc.id, "state": doc.state}}, status=201)

    @http.route("/api/v1/ecf/receive", type="http", auth="public", methods=["POST"], csrf=False)
    def receive_ecf(self, **kwargs):
        auth, err = self._authenticate(["ecf.receive"])
        if err:
            return err
        try:
            payload = json.loads(request.httprequest.data.decode() or "{}")
        except Exception:
            return _error("invalid_json", _("JSON inválido."))
        xml = payload.get("xml")
        if not xml:
            return _error("xml_required", _("Campo xml requerido."))
        Rec = request.env["justech.ecf.inbound.document"].sudo()
        try:
            rec = Rec.receive_xml(
                company=auth["company"],
                xml_text=xml,
                auto_draft_invoice=bool(payload.get("create_draft_invoice")),
                source="api",
                token=auth["token"],
            )
        except Exception as exc:
            self._audit(auth["token"], "receive_error", auth["company"], False, str(exc)[:300])
            return _error("receive_failed", str(exc)[:300], 422)
        self._audit(auth["token"], "receive", auth["company"], True, str(rec.id))
        return _json(
            {
                "data": {
                    "id": rec.id,
                    "state": rec.state,
                    "duplicate": rec.is_duplicate,
                    "issuer_rnc": rec.issuer_rnc,
                    "receiver_rnc": rec.receiver_rnc,
                    "e_ncf": rec.e_ncf,
                    "draft_move_id": rec.draft_move_id.id if rec.draft_move_id else False,
                }
            },
            status=201,
        )
