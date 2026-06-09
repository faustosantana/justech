"""Cliente Microsoft 365 — fachada de integración (sin Graph real en Fase 4)."""

from __future__ import annotations

from integrations.microsoft365.config import DEFAULT_APP_SCOPES, DEFAULT_READ_SCOPES, M365Config
from integrations.microsoft365.graph_client import GraphClient, NOT_CONNECTED

from .calendar import M365CalendarService
from .documents import M365DocumentsService
from .onedrive import M365OneDriveService
from .outlook import M365OutlookService
from .sharepoint import M365SharePointService
from .teams import M365TeamsService


class M365Client:
    """
    Punto de entrada M365 para JAIOS.

    Arquitectura futura:
    - OAuth / refresh tokens por usuario
    - Permisos delegados vs aplicación
    - Hermes Memory + Qdrant para indexación
    - JAIOS Assistant como consumidor unificado
    """

    def __init__(self, config: M365Config):
        self.config = config
        self._graph: GraphClient | None = None

    @property
    def connected(self) -> bool:
        return False

    @property
    def message(self) -> str:
        return NOT_CONNECTED

    def graph(self, *, user_id: str | None = None) -> GraphClient:
        if self._graph is None:
            self._graph = GraphClient(self.config, user_id=user_id)
        return self._graph

    @property
    def outlook(self) -> M365OutlookService:
        return M365OutlookService(self)

    @property
    def sharepoint(self) -> M365SharePointService:
        return M365SharePointService(self)

    @property
    def onedrive(self) -> M365OneDriveService:
        return M365OneDriveService(self)

    @property
    def calendar(self) -> M365CalendarService:
        return M365CalendarService(self)

    @property
    def teams(self) -> M365TeamsService:
        return M365TeamsService(self)

    @property
    def documents(self) -> M365DocumentsService:
        return M365DocumentsService(self)

    def required_config(self) -> dict:
        return {
            "read_only": self.config.read_only,
            "redirect_uri": self.config.redirect_uri,
            "missing_env_keys": self.config.missing_keys(),
            "delegated_scopes": list(DEFAULT_READ_SCOPES),
            "application_scopes": list(DEFAULT_APP_SCOPES),
            "oauth_ready": False,
            "graph_ready": False,
            "multi_user_ready": False,
            "indexing_ready": False,
            "enterprise_search_ready": False,
        }

    async def health(self) -> dict:
        return {
            "connected": False,
            "read_only": self.config.read_only,
            "message": NOT_CONNECTED,
            "configured": self.config.is_configured(),
            "required_config": self.required_config(),
        }
