# PLAN_ESTABILIZACION — Primeras 72 horas

## Objetivo

Mantener operación estable tras go-live Justech Fiscal v1.0 y detectar regresiones antes de que impacten DGII/caja.

## Monitoreo (cada turno / 8h)

| Señal | Umbral de alerta |
|-------|------------------|
| Log ERROR/CRITICAL | Cualquier spike vs baseline |
| Facturas posted sin NCF | > 0 |
| Cron padrón | Fallo o `failure_count` > 0 |
| Mail exception | Crecimiento sostenido |
| Disco | > 85% |
| Memoria / workers | Reinicios repetidos |

## Incidentes — severidad

| Severidad | Ejemplo | Acción |
|-----------|---------|--------|
| Sev-1 | No se puede facturar / NCF roto | War room; considerar rollback |
| Sev-2 | Reporte DGII falla; padrón rojo | Fix controlado en ventana; sin hotfixes ciegos |
| Sev-3 | Warning UX / menú | Backlog; no tocar PROD fuera de cambio menor aprobado |

## Escalamiento

1. Operador / Admin Sistema detecta.
2. Contador / Responsable Fiscal confirma impacto fiscal.
3. Arquitecto Justech decide fix vs rollback.
4. Sponsor aprueba cualquier cambio en PROD.

## Ritual 72h

- **H+4:** checklist post-prod completo.
- **H+24:** revisar NCF del día + 606/607 parcial.
- **H+48:** revisar crons + mail + salud fiscal.
- **H+72:** informe de estabilización en `/evidence/` y decisión: estable / observación / rollback diferido.

## Prohibido en las 72h

- Refactors, features nuevas, merges no planificados.
- Importaciones masivas de padrón en horario pico sin ventana.
- Edición directa de movimientos contables posted.
