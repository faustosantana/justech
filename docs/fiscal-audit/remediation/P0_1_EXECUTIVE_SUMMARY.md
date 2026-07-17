# P0.1 — Resumen ejecutivo

**Fecha:** 2026-07-17  
**Ámbito:** DEV only (`justech_dev` / `erp.justech.do`)  
**Hallazgo:** FISC-AUD-001 Dual-stack NCF  
**Prod:** NO modificada  
**Baseline alertas NCF:** INTACTA (`aaea7f5…` / `ncf-alerts-baseline-v1`)

## Decisión

**Estrategia B (adaptada):** Justech = fuente de verdad para **emisión**; LATAM = entrada para **compras recibidas**; FDP = fachada de **lectura** unificada.

## Cambios mínimos aplicados

1. Desactivar feature flag `ncf_dual_write` (deja de escribir NCF/tipo en LATAM al asignar Justech).
2. Gate de publicación: prefijo del tipo ≠ prefijo del NCF → `UserError` (ventas + compras emitidas + recibidas).
3. Default seguro: si no existe el flag, `is_dual_write_enabled` → **False**.
4. Tests de regresión canónica + sync unidireccional.
5. Inventario de 19–20 históricos prefijo≠tipo **sin modificar**.

## Resultado DEV

| Check | Estado |
|---|---|
| Backup + restore | PASS |
| Escritura dual NCF | eliminada (flag off) |
| Históricos tocados | 0 |
| Secuencias consumidas por auditoría | 0 |
| Baseline alertas | intacta |

## Próximo paso

Saneamiento histórico separado (P1) + autorización para Prod.
