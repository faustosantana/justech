# 07 — Plan de remediación (NO IMPLEMENTAR sin autorización)

## Principios

- Corrección mínima y multiempresa-safe.
- No romper facturación, cotizaciones, CRM, compras, ventas, portal, Enterprise.
- Respetar `company_id` del documento como fuente de verdad de identidad.
- Respetar SMTP por dominio/empresa en Prod.
- Primero DEV → UAT → solo entonces Prod.

## Fase A — Datos (configuración)

1. Para cada `helpdesk.team`, alinear `alias_domain_id` al dominio de `company_id`:
   - JUSTECH team 1: `customer-care@justech.do` (o alias dedicado JUSTECH), **no** `just-offices.com`.
   - JUSTECH team 6: dominio `justech.do`.
   - Omni team 3 → `solutionsomni.com`.
   - PlugSafe team 4 → `plugsafeservices.com`.
2. Verificar DNS/MX/SPOOFing/M365 send-as **antes** de cambiar Prod.
3. No tocar SMTP passwords ni mail servers en el mismo cambio.

## Fase B — Plantillas

1. Eliminar hardcodes `Soporte Justech <asistencia@justech.do>` en templates 72/80/81/82.
2. Sustituir por expresión company-aware, p. ej. preferir:
   - `object.company_id.email_formatted` **o**
   - alias del team **solo si** `alias_domain` ∈ dominios de la company.
3. Mantener Reply-To humano vía política (no hardcode).

## Fase C — Código política

1. Desplegar en DEV la política **19.0.1.1.0** (selección por `record_company_id` / `document.company_id` **antes** que dominio From).
2. Añadir regla explícita de no-fuga:
   - Si `mail.model == helpdesk.ticket` y `record.company_id`, forzar policy de esa company aunque el From sea de otro dominio.
3. Tests: 4 compañías × team correcto / team mal-aliasado × template closed/received.
4. Flag ICP para rollback: `justech_mail.outgoing_policy_enabled`.

## Fase D — Verificación

| Check | Criterio PASS |
|---|---|
| Ticket JUSTECH team 1 | From dominio justech.do (o notifications@justech.do) |
| Ticket Just Office | From just-offices.com |
| Ticket PlugSafe / Omni | Dominio propio, no Just Office ni Justech |
| Factura / SO / PO / CRM | Sin cambio de From no relacionado |
| SMTP Prod | from_filter coincide con company del documento |
| Logo | Misma company que From |

## Fuera de alcance de esta remediación

- Cambiar catchall global sin diseño.
- Reescribir todo mail.thread.
- Unificar todos los SMTP en uno solo.
- “Parche” que fuerce siempre Justech.

## Estado actual

**Implementación: BLOQUEADA** hasta autorización expresa del usuario.
