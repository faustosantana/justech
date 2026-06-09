# Integraciones — JAIOS Fase 1

## Odoo

**Ubicación:** `integrations/odoo/`

```python
from integrations.odoo import OdooClient

client = OdooClient(tenant_id="...")
status = await client.test_connection()
```

**Variables de entorno:** `ODOO_URL`, `ODOO_DB`, `ODOO_USERNAME`, `ODOO_API_KEY`

**Endpoint API:** `POST /api/v1/integrations/odoo/test-connection`

---

## n8n

**Ubicación:** `integrations/n8n/`

Automatización vía webhooks. n8n corre como servicio Docker con base de datos dedicada `jaios_n8n`.

```python
from integrations.n8n import N8nClient

client = N8nClient(tenant_id="...")
result = await client.trigger_workflow("workflow-id", payload={})
```

**Variables:** `N8N_WEBHOOK_URL`, `N8N_API_KEY`

**Endpoint API:** `POST /api/v1/integrations/n8n/trigger/{workflow_id}`

---

## DGCP

**Ubicación:** `integrations/dgcp/`

Conector para datos abiertos de la Dirección General de Contrataciones Públicas (República Dominicana).

```python
from integrations.dgcp import DGCPClient

client = DGCPClient()
health = await client.health_check()
```

**Variables:** `DGCP_API_BASE_URL`, `DGCP_API_KEY`

**Endpoint API:** `GET /api/v1/integrations/dgcp/health`

---

## Microsoft 365 (Fase 4 — planificado)

**Ubicación:** `integrations/microsoft365/`

Stub para Microsoft Graph. Sin endpoints ni UI hasta Fase 4.

**Variables:** `M365_TENANT_ID`, `M365_CLIENT_ID`, `M365_CLIENT_SECRET`

---

## Intelligence modules (Fase 4–7)

**Ubicación:** `integrations/intelligence/`

Interfaces y dataclasses para módulos futuros: Tasks, Notificaciones, Work Hub, Enterprise Search, Document Repository, Supplier/Price Intelligence, Hermes Memory, Multi-Agent.

Ver [`roadmap.md`](roadmap.md) para dependencias y orden de entrega.

---

## Estado por fase

| Integración | Fase | Estado |
|-------------|------|--------|
| DGCP | 2 | Productivo |
| Odoo | 3 | Read-only productivo |
| Microsoft 365 | 4 | Stub |
| n8n | 7 | Webhook trigger |
| Intelligence stubs | 4–7 | Interfaces sin implementación |
