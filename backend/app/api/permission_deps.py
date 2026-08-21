"""Constantes Depends para PR-1.3b — aplicar en decoradores de rutas sensibles."""

from __future__ import annotations

from fastapi import Depends

from app.api.deps import RequirePermission

# DGCP / Licitaciones
DGCP_VIEW = [Depends(RequirePermission("view_dgcp"))]
DGCP_MUTATE = [Depends(RequirePermission("mutate_dgcp"))]

# Odoo
ODOO_VIEW = [Depends(RequirePermission("view_odoo"))]
ODOO_MUTATE = [Depends(RequirePermission("mutate_odoo"))]

# Microsoft 365 (operaciones Graph — no DocumentAccessService read)
M365_VIEW = [Depends(RequirePermission("view_m365"))]
M365_MUTATE = [Depends(RequirePermission("mutate_m365"))]

# Documentos (hub, empresas, acceso unificado lectura)
DOCS_VIEW = [Depends(RequirePermission("view_documents"))]
DOCS_MUTATE = [Depends(RequirePermission("mutate_documents"))]

# Asistente / Hermes
ASSISTANT_VIEW = [Depends(RequirePermission("view_assistant"))]
ASSISTANT_MUTATE = [Depends(RequirePermission("mutate_assistant"))]

# Rutas excluidas de permisos de dominio (solo CurrentUser o público):
# - /documents/public/*
# - /m365/oauth/callback (sin JWT)
# - /m365/webhooks/*
# - /m365/operative/webhooks/*
# - GET */health (monitoreo)
