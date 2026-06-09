# JAIOS — Roadmap próximas fases

Documento estratégico para producción multiempresa, Assistant inteligente, Desktop y proveedores externos.

## Fase A — Company Context Global

**Estado:** Corrección aplicada (validación parcial)

- API `/api/v1/company-context` GET/PUT
- `/api/v1/company-context/allowed`
- Admin `/api/v1/admin/users/{id}/companies`
- Selector en header y dashboard
- Filtrado Odoo multiempresa (`company_ids in domain`)
- Search auto-filtro por empresa activa

**Pendiente:** filtros Documents/Tasks/DGCP por empresa Odoo; login con selector; permisos Marieli vs Fausto en UI admin.

## Fase B — Assistant Conversational Memory + Synonyms

**Estado:** Corrección aplicada

- Memoria de sesión (`conversation_id`)
- Follow-ups: «¿A quiénes?», «¿Y a qué precio?»
- `CustomerEntityResolver` con alias Farma Trix, Ademi, Capital DBG
- Contexto empresa en respuestas

**Pendiente:** confirmación interactiva multi-candidato en UI; embeddings semánticos.

## Fase C — UX/UI Premium Dashboard

**Estado:** Validación parcial

- Dashboard ejecutivo, KPIs, assistant proactivo, avatar, sidebar agrupado

**Pendiente:** breadcrumbs, dark mode, vigencias como submódulo.

## Fase D — Companies/Suppliers funcional

**Estado:** Corrección aplicada

- CRUD empresas/proveedores en `/empresas`

**Pendiente:** seed desde precios/Odoo; acciones masivas export.

## Fase E — Desktop App Windows/Mac

**Estado:** Estructura Tauri en `desktop/`

- Tray, token keychain, `make desktop-dev/build-mac/build-windows`

**Pendiente:** build nativo validado; atajo global Cmd+Shift+J.

## Fase F — Supplier Connectors (Ingram/Omega)

**Estado:** Diseño

- Interface `SupplierConnector`: search_products, get_price, get_stock, sync_catalog

**Pendiente:** implementación Ingram API / import Excel Omega.

## Fase G — Hermes Worker Integration

**Estado:** Diseño

Hermes como worker backend para:

- indexar listas de precios pesadas
- analizar pliegos DGCP
- embeddings locales
- batch vigencias

Flujo: JAIOS → cola → Hermes → resultado estructurado → JAIOS DB

## Fase H — Scraper controlado

Reglas: robots/terms, rate limit, cache, auditoría, fuente visible, sin bypass auth.

Marcar resultados: «Fuente web — requiere verificación».

## Fase I — Odoo quote automation controlada

Borradores internos → validación humana → Odoo (read-only hasta aprobación).

## Fase J — M365 real

OAuth Azure AD, correo, calendario, adjuntos en search.

---

**Veredicto global:** Validación parcial — pendiente revisión visual Fausto y QA self-heal post-migración 018.
