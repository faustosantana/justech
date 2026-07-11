# Fase A — cierre roles / errores / padrón (2026-07-11)

## 8 errores identificados (antes del cierre)

| # | Empresa | Código | Tipo |
|---|---------|--------|------|
| 1 | JUSTECH | PARTNER_INVALID_RNC | Real |
| 2 | JUSTECH | POSTED_MISSING_NCF (4250→FC/2026/00374) | Real |
| 3 | JUSTECH | POSTED_MISSING_NCF (FC/2026/00373) | Real |
| 4 | JUSTECH | POSTED_MISSING_NCF (FC/2026/00371) | Real |
| 5 | JUSTECH | PADRON_ISSUE running huérfano | Falso positivo |
| 6 | PlugSafe | PADRON_ISSUE running huérfano | Falso positivo |
| 7 | Omni | PADRON_ISSUE running huérfano | Falso positivo |
| 8 | Just Office | PADRON_ISSUE running huérfano | Falso positivo |

## Falsos positivos corregidos

Importación `running` huérfana con 781980 registros → cerrada; estado **Padrón global cargado y vigente** en 4/4.

## Errores reales restantes (JUSTECH = 4)

1. **PARTNER_INVALID_RNC** — FC/2026/00397 / partner P2 AUDIT — corregir RNC.
2–4. **POSTED_MISSING_NCF** — FC/2026/00374, 00373, 00371 — asignar NCF o anular según política.

## Roles

- Responsable: abre Centro modo `officer` (lectura + revalidación; sin padrón/flags/permisos).
- Usuario: abre Centro modo `user` (operativo; sin admin NCF/padrón/flags).
- Contador/Ventas/Compras: sin menú Centro; AccessError si invocan apertura.

## Resultado

`FASE_A_CLOSED` en justech_dev. Sin commit. Sin Prod.
