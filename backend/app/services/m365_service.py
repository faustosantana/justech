"""Microsoft 365 Intelligence Center — servicio base (sin Graph real)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas.m365 import (
    M365ConfigKey,
    M365Diagnostics,
    M365HealthResponse,
    M365ListResponse,
    M365RequiredConfig,
    M365SearchResponse,
    M365SetupStep,
    M365StatusResponse,
    NOT_CONNECTED_MESSAGE,
)
from app.services.audit_service import AuditService
from integrations.microsoft365.client import M365Client
from integrations.microsoft365.config import M365Config


class M365Service:
    def __init__(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self._audit_svc = AuditService(db)

    def _client(self) -> M365Client:
        return M365Client(
            M365Config(
                tenant_id=settings.m365_tenant_id,
                client_id=settings.m365_client_id,
                client_secret=settings.m365_client_secret,
                redirect_uri=settings.m365_redirect_uri,
                read_only=settings.m365_read_only,
            )
        )

    def _required_config(self) -> M365RequiredConfig:
        client = self._client()
        raw = client.required_config()
        config_keys = [
            M365ConfigKey(
                key="M365_TENANT_ID",
                label="Tenant ID (Azure AD)",
                description="Identificador del directorio Microsoft Entra ID",
                configured=bool(settings.m365_tenant_id.strip()),
            ),
            M365ConfigKey(
                key="M365_CLIENT_ID",
                label="Client ID (App Registration)",
                description="ID de la aplicación registrada en Azure",
                configured=bool(settings.m365_client_id.strip()),
            ),
            M365ConfigKey(
                key="M365_CLIENT_SECRET",
                label="Client Secret",
                description="Secreto de aplicación (almacenamiento seguro futuro)",
                configured=bool(settings.m365_client_secret.strip()),
            ),
            M365ConfigKey(
                key="M365_REDIRECT_URI",
                label="Redirect URI",
                description="Callback OAuth tras consentimiento del usuario",
                configured=bool(settings.m365_redirect_uri.strip()),
            ),
        ]
        return M365RequiredConfig(
            read_only=raw["read_only"],
            redirect_uri=raw["redirect_uri"],
            missing_env_keys=raw["missing_env_keys"],
            config_keys=config_keys,
            delegated_scopes=raw["delegated_scopes"],
            application_scopes=raw["application_scopes"],
            oauth_ready=raw["oauth_ready"],
            graph_ready=raw["graph_ready"],
            multi_user_ready=raw["multi_user_ready"],
            indexing_ready=raw["indexing_ready"],
            enterprise_search_ready=raw["enterprise_search_ready"],
            hermes_memory_ready=False,
            qdrant_ready=False,
        )

    def _diagnostics(self) -> M365Diagnostics:
        cfg = self._client().config
        return M365Diagnostics(
            api_reachable=True,
            graph_configured=cfg.is_configured(),
            oauth_implemented=False,
            graph_implemented=False,
            read_only_enforced=settings.m365_read_only,
            audit_enabled=True,
            notes=[
                "Fase 4: estructura base sin Microsoft Graph real.",
                "OAuth, refresh tokens y multiusuario pendientes.",
                "Indexación documental → Qdrant planificada.",
                "Hermes Memory como capa de contexto empresarial.",
            ],
        )

    def _setup_steps(self) -> list[M365SetupStep]:
        return [
            M365SetupStep(
                step=1,
                title="Registrar aplicación en Azure",
                description="Crear App Registration en Microsoft Entra ID con permisos delegados de lectura.",
                status="pending",
            ),
            M365SetupStep(
                step=2,
                title="Configurar variables de entorno",
                description="Completar M365_TENANT_ID, M365_CLIENT_ID, M365_CLIENT_SECRET y M365_REDIRECT_URI.",
                status="pending",
            ),
            M365SetupStep(
                step=3,
                title="Conectar cuenta Microsoft 365",
                description="OAuth por usuario JAIOS con consentimiento y refresh tokens.",
                status="pending",
            ),
            M365SetupStep(
                step=4,
                title="Validar permisos y modo lectura",
                description="Confirmar M365_READ_ONLY=true y auditoría de consultas.",
                status="pending",
            ),
            M365SetupStep(
                step=5,
                title="Habilitar búsqueda e indexación",
                description="Enterprise Search, Qdrant y JAIOS Assistant con contexto M365.",
                status="pending",
            ),
        ]

    async def _log_audit(self, action: str, details: dict | None = None) -> None:
        await self._audit_svc.log(
            action=action,
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            resource_type="m365",
            details=details or {},
        )

    async def health(self) -> M365HealthResponse:
        await self._log_audit("m365.status_checked", {"endpoint": "health"})
        return M365HealthResponse(
            connected=False,
            read_only=settings.m365_read_only,
            message=NOT_CONNECTED_MESSAGE,
            required_config=self._required_config(),
            diagnostics=self._diagnostics(),
        )

    async def status(self) -> M365StatusResponse:
        await self._log_audit("m365.status_checked", {"endpoint": "status"})
        return M365StatusResponse(
            connected=False,
            read_only=settings.m365_read_only,
            message=NOT_CONNECTED_MESSAGE,
            required_config=self._required_config(),
            setup_steps=self._setup_steps(),
            diagnostics=self._diagnostics(),
        )

    async def _disconnected_list(self, *, resource: str) -> M365ListResponse:
        await self._log_audit("m365.not_connected", {"resource": resource})
        return M365ListResponse(
            items=[],
            total=0,
            connected=False,
            read_only=settings.m365_read_only,
            message=NOT_CONNECTED_MESSAGE,
            required_config=self._required_config(),
        )

    async def outlook_messages(self, *, search: str = "", limit: int = 50) -> M365ListResponse:
        return await self._disconnected_list(resource="outlook.messages")

    async def sharepoint_sites(self, *, search: str = "", limit: int = 50) -> M365ListResponse:
        return await self._disconnected_list(resource="sharepoint.sites")

    async def onedrive_files(self, *, search: str = "", limit: int = 50) -> M365ListResponse:
        return await self._disconnected_list(resource="onedrive.files")

    async def calendar_events(self, *, limit: int = 50) -> M365ListResponse:
        return await self._disconnected_list(resource="calendar.events")

    async def teams(self, *, limit: int = 50) -> M365ListResponse:
        return await self._disconnected_list(resource="teams")

    async def documents(self, *, search: str = "", limit: int = 50) -> M365ListResponse:
        return await self._disconnected_list(resource="documents")

    async def search(self, query: str, *, limit: int = 25) -> M365SearchResponse:
        await self._log_audit("m365.search_requested", {"query": query[:200], "limit": limit})
        await self._log_audit("m365.not_connected", {"resource": "search"})
        return M365SearchResponse(
            query=query,
            hits=[],
            total=0,
            connected=False,
            read_only=settings.m365_read_only,
            message=NOT_CONNECTED_MESSAGE,
            required_config=self._required_config(),
        )
