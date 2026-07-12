"""Clientes DGII desacoplados.

Fuentes oficiales (Descripción Técnica Servicios DGII):
- Autenticación: https://ecf.dgii.gov.do/{ambiente}/autenticacion
  Endpoints: /api/autenticacion/semilla , /api/autenticacion/validarsemilla
- Recepción e-CF: https://ecf.dgii.gov.do/{ambiente}/recepcion
  Endpoint: /api/facturaselectronicas
- TrackID: .../trackids/api/trackids/consulta
Producción nunca se llama sin Gate explícita.
"""

import json
import uuid
from datetime import datetime

from odoo import api, models, _
from odoo.exceptions import UserError

ENV_BASE = {
    "testecf": "https://ecf.dgii.gov.do/testecf",
    "certecf": "https://ecf.dgii.gov.do/certecf",
    "ecf": "https://ecf.dgii.gov.do/ecf",
}


class JustechEcfDgiiClient(models.AbstractModel):
    _name = "justech.ecf.dgii.client"
    _description = "Cliente DGII e-CF"

    @api.model
    def _get_config(self, company):
        return self.env["justech.ecf.company.config"].search([("company_id", "=", company.id)], limit=1)

    @api.model
    def get_adapter(self, company):
        cfg = self._get_config(company)
        if not cfg:
            return "mock"
        if cfg.dgii_environment == "ecf" and not cfg.production_gate_unlocked:
            raise UserError(_("Producción DGII bloqueada por Gate de Producción."))
        return cfg.dgii_environment or "mock"

    @api.model
    def authenticate(self, company):
        env = self.get_adapter(company)
        if env == "mock":
            return {"token": "mock-token-%s" % uuid.uuid4().hex[:8], "environment": "mock", "mode": "simulated"}
        if env == "ecf":
            raise UserError(_("Llamadas a Producción DGII no permitidas en este entorno de desarrollo."))
        # Certificación / pre-certificación: requieren certificado y red — no se invocan sin credenciales.
        raise UserError(
            _(
                "Ambiente %(env)s requiere credenciales/certificado autorizados. "
                "Use mock para pruebas locales o configure certificación con autorización explícita. "
                "URL base oficial: %(url)s/autenticacion"
            )
            % {"env": env, "url": ENV_BASE.get(env, "")}
        )

    @api.model
    def send_ecf(self, document):
        document.ensure_one()
        env = self.get_adapter(document.company_id)
        if env == "mock":
            track = "MOCK-%s" % uuid.uuid4().hex[:12].upper()
            document.write(
                {
                    "state": "accepted",
                    "track_id": track,
                    "dgii_status": "Aceptado",
                    "dgii_message": _("Simulación mock — sin llamada real a DGII."),
                    "attempt_count": document.attempt_count + 1,
                }
            )
            document._log_event("send_mock", message=track)
            return {"track_id": track, "status": "accepted", "mode": "mock"}
        if env == "ecf":
            raise UserError(_("Envío a Producción DGII bloqueado."))
        raise UserError(
            _(
                "Envío a %(env)s no ejecutado: faltan credenciales de certificación autorizadas. "
                "No se realizó llamada externa."
            )
            % {"env": env}
        )

    @api.model
    def consulta_track_id(self, document):
        document.ensure_one()
        env = self.get_adapter(document.company_id)
        if env == "mock":
            return {"track_id": document.track_id, "status": document.dgii_status or "Aceptado", "mode": "mock"}
        raise UserError(_("Consulta real a DGII no habilitada sin credenciales autorizadas."))

    @api.model
    def service_catalog(self):
        """Catálogo de URLs oficiales documentadas (no inventadas)."""
        return {
            "environments": ENV_BASE,
            "services": [
                {"code": "autenticacion", "path": "/autenticacion", "endpoints": ["/api/autenticacion/semilla", "/api/autenticacion/validarsemilla"]},
                {"code": "recepcion", "path": "/recepcion", "endpoints": ["/api/facturaselectronicas"]},
                {"code": "trackids", "path": "/trackids", "endpoints": ["/api/trackids/consulta"]},
                {"code": "consultaresultado", "path": "/consultaresultado", "endpoints": ["/api/consultas/estado"]},
                {"code": "consultaestado", "path": "/consultaestado", "endpoints": ["/api/consultas"]},
                {"code": "anulacionrangos", "path": "/anulacionrangos", "endpoints": ["/api/operaciones/anularrango"]},
                {"code": "directorio", "path": "/directorio", "endpoints": ["/api/consultas/obtenerdirectorioporrnc"]},
            ],
            "source": "Descripcion Tecnica Servicios DGII.pdf (portal DGII)",
            "retrieved_at": datetime.utcnow().isoformat() + "Z",
        }
