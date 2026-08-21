# DGCP Historical Intelligence 360°

Documentación de cierre del módulo de inteligencia histórica sobre adjudicaciones DGCP en JAIOS.

## Fuentes

- Índice local: tabla `dgcp_historical_awards` (contratos + artículos DGCP).
- API oficial DGCP (`/contratos`, `/contratos/articulos`, `/procesos`).
- **No** se inventa RNC ni identidad. Si la fuente no publica RNC → “No disponible en la fuente”.

## Identity resolution

Prioridad proveedor:

1. RNC exacto verificado (`rnc-…`) + `rnc_source`
2. RPE exacto (`rpe-…`)
3. ID DGCP (`dgcp-supplier-…`) si existiera
4. Nombre normalizado (`name-{slug}-{digest}`) — confianza **sugerida**

Prioridad institución:

1. `buyer_institution_code` (`code-…`)
2. Identificador DGCP
3. RNC institucional (si existiera)
4. Nombre normalizado solo como candidato

`display_name_original` se conserva; la normalización es solo para matching interno.

## Dedup rules

- **Auto-merge** solo con RNC / RPE / código DGCP exactos.
- Nombre similar → `POSSIBLE_DUPLICATE` / `REVIEW_REQUIRED` (nunca merge automático).
- Merges lógicos auditados en `dgcp_historical_identity_actions` (reversibles; no borran histórico).
- Admin: `/configuracion/dgcp/calidad-datos`

## Comparación

- API: `POST /dgcp/intelligence/suppliers/compare` (máx. 3 keys).
- UI: `/dgcp/intelligence/compare`
- Desde ranking / perfil / institución (contexto opcional `institution_key`).
- Solo hechos históricos; **sin** score de riesgo/reputación/favoritismo.

## RNC provenance

Campos posibles: `DGCP_CONTRACT`, `DGCP_SUPPLIER`, `DGCP_RPE`, `OTHER_OFFICIAL`, `NONE`.

Auditoría 2026-08 sobre índice Justech Demo (~18.5k líneas): **0** RNC en payload oficial (`contrato` expone `rpe` + `razon_social`, no RNC).

Perfil puede estar **VERIFICADO** por RPE aunque RNC falte.

## Source health

- Endpoint: `GET /dgcp/intelligence/source-health`
- Estados: `AVAILABLE` / `DEGRADED` / `UNAVAILABLE`
- Live UAT puede quedar `LIVE_SOURCE_UNAVAILABLE` (p. ej. HTTP 502) sin marcar FAIL del producto si el índice local es estable.

## Jobs / wrapper

Estados: `SUCCESS`, `FAILED`, `TIMEOUT`, `COMPLETED_AFTER_TIMEOUT`, `SOURCE_UNAVAILABLE` (+ legacy `completed`/`failed`).

Completion marker (`completed_at`, `rows_processed`, `duration_ms`, `result_hash`, `result_meta`) se persiste al terminar. Un timeout de shell **posterior** no degrada `SUCCESS`.

Retry automático solo si el job **no** está en éxito.

## Cache

Claves de perfil usan `supplier_identity_key` / `institution_identity_key` (stable keys). Invalidación al merge/unmerge.

## Known limitations

- RNC incompleto cuando DGCP no lo publica.
- Live re-UAT depende de disponibilidad de datosabiertos DGCP.
- Candidatos fuzzy por nombre requieren revisión humana (admin).
- No toca CRM / Odoo / `sale.order` / flujo de licitaciones comerciales.
