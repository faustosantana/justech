"""Administración Microsoft 365 — config, pruebas, webhooks."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.m365_admin import (
    M365AdminConfigResponse,
    M365ConnectionTestResponse,
    M365GraphPermissionCheck,
    M365GraphPermissionsResponse,
    M365WebhookRenewResponse,
)
from app.services.m365_config_resolver import resolve_m365_config, update_m365_tenant_overrides
from app.services.m365_oauth_service import M365OAuthService
from integrations.microsoft365.config import DEFAULT_APP_SCOPES, DEFAULT_READ_SCOPES
from integrations.microsoft365.graph_client import GraphClient
from integrations.microsoft365.oauth import M365OAuthError
from integrations.microsoft365.schemas import M365OAuthTokens

SCOPE_DESCRIPTIONS: dict[str, str] = {
    "Mail.Read": "Leer correos",
    "Mail.ReadWrite": "Leer y modificar correos",
    "Mail.Send": "Enviar correos",
    "Calendars.Read": "Leer calendario",
    "Calendars.ReadWrite": "Leer y modificar calendario",
    "Contacts.Read": "Leer contactos",
    "Files.Read": "OneDrive (delegado)",
    "Files.ReadWrite": "OneDrive lectura/escritura (delegado)",
    "Files.Read.All": "OneDrive (todas las unidades)",
    "Files.ReadWrite.All": "OneDrive lectura/escritura (todas las unidades)",
    "Sites.Read.All": "SharePoint lectura",
    "Sites.ReadWrite.All": "SharePoint lectura/escritura",
    "Team.ReadBasic.All": "Teams",
    "Channel.ReadBasic.All": "Canales Teams",
    "ChannelMessage.Read.All": "Mensajes de canal Teams",
    "User.Read": "Perfil usuario",
    "offline_access": "Refresh token",
}


class M365AdminService:
    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID, actor_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.actor_id = actor_id

    async def get_config(self) -> M365AdminConfigResponse:
        _, meta = await resolve_m365_config(self.db, self.tenant_id)
        return M365AdminConfigResponse(**meta)

    async def update_config(
        self, *, client_secret: str | None = None, webhook_client_state: str | None = None
    ) -> M365AdminConfigResponse:
        meta = await update_m365_tenant_overrides(
            self.db,
            self.tenant_id,
            client_secret=client_secret,
            webhook_client_state=webhook_client_state,
        )
        return M365AdminConfigResponse(**meta)

    async def test_connection(self) -> M365ConnectionTestResponse:
        cfg, _ = await resolve_m365_config(self.db, self.tenant_id)
        if not cfg.is_configured():
            return M365ConnectionTestResponse(
                ok=False,
                message="Faltan M365_TENANT_ID, M365_CLIENT_ID o M365_CLIENT_SECRET",
            )
        token = await M365OAuthService(self.db, self.tenant_id, self.actor_id).get_valid_access_token(
            self.actor_id
        )
        if token:
            graph = GraphClient(cfg, tokens=M365OAuthTokens(access_token=token))
            try:
                me = await graph.get_me()
                return M365ConnectionTestResponse(
                    ok=True,
                    message="Conexión Graph OK (usuario OAuth conectado)",
                    token_acquired=True,
                    graph_reachable=True,
                    user_display_name=me.get("displayName"),
                )
            except Exception as exc:
                return M365ConnectionTestResponse(
                    ok=False,
                    message=f"Token OAuth presente pero Graph falló: {exc}",
                    token_acquired=True,
                )
        return M365ConnectionTestResponse(
            ok=cfg.is_configured(),
            message="Azure configurado. Conecte un usuario vía OAuth en /m365 para probar Graph.",
            token_acquired=False,
        )

    def graph_permissions(self) -> M365GraphPermissionsResponse:
        delegated = [
            M365GraphPermissionCheck(
                scope=s,
                required=True,
                description=SCOPE_DESCRIPTIONS.get(s, s),
            )
            for s in DEFAULT_READ_SCOPES
            if s not in ("openid", "profile")
        ]
        application = [
            M365GraphPermissionCheck(scope=s, required=False, description=SCOPE_DESCRIPTIONS.get(s, s))
            for s in DEFAULT_APP_SCOPES
        ]
        return M365GraphPermissionsResponse(
            delegated_scopes=delegated,
            application_scopes=application,
            admin_consent_required=True,
        )

    async def renew_webhooks(self) -> M365WebhookRenewResponse:
        from app.config import settings
        from app.services.m365_graph_webhook_service import M365GraphWebhookService

        if not settings.m365_webhook_url.strip():
            return M365WebhookRenewResponse(ok=False, message="M365_WEBHOOK_URL no configurado")
        cfg, _ = await resolve_m365_config(self.db, self.tenant_id)
        token = await M365OAuthService(self.db, self.tenant_id, self.actor_id).get_valid_access_token(
            self.actor_id
        )
        if not token:
            return M365WebhookRenewResponse(
                ok=False,
                message="Requiere usuario con OAuth conectado para crear suscripción Graph",
            )
        try:
            sub = await M365GraphWebhookService(cfg, token).renew_mail_subscription(
                notification_url=settings.m365_webhook_url,
                client_state=settings.m365_webhook_client_state,
            )
            return M365WebhookRenewResponse(
                ok=True,
                message="Suscripción Graph creada/renovada",
                subscription_id=sub.get("id"),
                expiration=sub.get("expirationDateTime"),
            )
        except Exception as exc:
            return M365WebhookRenewResponse(ok=False, message=str(exc))
