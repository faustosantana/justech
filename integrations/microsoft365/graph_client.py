"""Microsoft Graph client — stub Fase 4 (sin llamadas reales)."""

from __future__ import annotations

from integrations.microsoft365.config import M365Config
from integrations.microsoft365.schemas import M365OAuthTokens

NOT_CONNECTED = "Microsoft 365 no conectado"


class GraphClient:
    """
    Cliente Microsoft Graph (futuro).

    Preparado para:
    - OAuth 2.0 authorization code + refresh tokens
    - Multiusuario (token por usuario JAIOS)
    - Rate limiting (Retry-After / throttling)
    - Auditoría de cada request Graph
    - Indexación documental → Qdrant
    - Enterprise Search unificado
    """

    GRAPH_BASE = "https://graph.microsoft.com/v1.0"

    def __init__(
        self,
        config: M365Config,
        *,
        tokens: M365OAuthTokens | None = None,
        user_id: str | None = None,
    ):
        self.config = config
        self.tokens = tokens
        self.user_id = user_id

    @property
    def connected(self) -> bool:
        """Fase 4: siempre False hasta implementar OAuth + Graph."""
        return False

    async def get_me(self) -> dict:
        raise NotImplementedError(NOT_CONNECTED)

    async def request(self, method: str, path: str, **kwargs) -> dict:
        if self.config.read_only and method.upper() not in ("GET", "HEAD"):
            raise PermissionError("M365_READ_ONLY: operación de escritura bloqueada")
        raise NotImplementedError(NOT_CONNECTED)
