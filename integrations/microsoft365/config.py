"""Configuración Microsoft 365 / Microsoft Graph."""

from __future__ import annotations

from pydantic import BaseModel, Field

# Permisos delegados previstos (OAuth) — solo lectura en Fase 4+
DEFAULT_READ_SCOPES: tuple[str, ...] = (
    "openid",
    "profile",
    "offline_access",
    "Mail.Read",
    "Calendars.Read",
    "Files.Read.All",
    "Sites.Read.All",
    "Team.ReadBasic.All",
    "ChannelMessage.Read.All",
    "User.Read",
)

# Permisos de aplicación previstos (admin consent) — indexación / Enterprise Search
DEFAULT_APP_SCOPES: tuple[str, ...] = (
    "Mail.Read",
    "Calendars.Read",
    "Files.Read.All",
    "Sites.Read.All",
)


class M365Config(BaseModel):
    tenant_id: str = Field(default="", description="Azure AD Tenant ID")
    client_id: str = Field(default="", description="App registration Client ID")
    client_secret: str = Field(default="", description="Client secret (confidencial)")
    redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/m365/auth/callback",
        description="OAuth redirect URI",
    )
    read_only: bool = Field(default=True, description="Bloquear operaciones de escritura en Graph")

    def is_configured(self) -> bool:
        return bool(self.tenant_id.strip() and self.client_id.strip() and self.client_secret.strip())

    def missing_keys(self) -> list[str]:
        missing: list[str] = []
        if not self.tenant_id.strip():
            missing.append("M365_TENANT_ID")
        if not self.client_id.strip():
            missing.append("M365_CLIENT_ID")
        if not self.client_secret.strip():
            missing.append("M365_CLIENT_SECRET")
        return missing
