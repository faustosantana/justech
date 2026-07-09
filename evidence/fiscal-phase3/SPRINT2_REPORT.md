# Fase 3A — Sprint 2 Report

**Rama:** `feature/fiscal-standard-phase3a`  
**Versión módulo:** `justech_l10n_do_ncf` 19.0.2.1.0  
**Entorno validado:** `justech_ncf_lab` @ erp.justech.do (207.244.242.58)  
**Fecha:** 2026-07-09

## Objetivo

Cerrar Sprint 2 del estándar fiscal Justech: administración, diagnóstico, duplicados v2.0,
reglas de negocio Adel, flujos NC/ND/compras, multiempresa y validación de integridad histórica.

## Entregables

| Componente | Estado |
|------------|--------|
| Centro de Administración Fiscal | ✅ |
| Diagnóstico fiscal read-only | ✅ |
| Duplicados v2.0 (Python) | ✅ |
| Reglas B14 / RD$250k / B16 | ✅ |
| ND B03, NC compra `in_refund` | ✅ |
| Multiempresa 4 compañías | ✅ |
| Integridad GL/pagos/conciliaciones | ✅ |
| Índice SQL v2.0 | 📋 Documentado — NO aplicado |

## Pruebas

```
justech_l10n_do_ncf: 37 tests — 0 failed, 0 errors
```

Checkpoint intermedio (parte 1): commit `a1080d9` — 27/27 PASS.

## Integridad histórica (read-only)

| Métrica | Valor |
|---------|-------|
| Asientos publicados | 2,255 |
| NCF publicados | 1,494 |
| GL débito = crédito | ✅ 85,656,868.89 |
| Conciliaciones parciales | 947 |
| Pagos activos | 677 |

**Histórico intacto** — sin alteración de movimientos, secuencias ni consumos previos.

## Índice SQL v2.0

Plan completo en [`NCF_INDEX_V2_PLAN.md`](./NCF_INDEX_V2_PLAN.md).  
**Requiere aprobación explícita** antes de cualquier ejecución en lab o clon.

## Rollback

1. Restaurar backup BD `justech_ncf_lab` previo al upgrade.
2. Checkout git `justech_l10n_do_ncf` 19.0.2.0.0 (checkpoint) o 19.0.1.8.0 (pre-Sprint 2).
3. `-u justech_l10n_do_ncf --stop-after-init`.

## Restricciones respetadas

- ❌ `justgroup.app` — no tocado
- ❌ `justech_dev` operativo — no tocado
- ❌ `main` / `development` — no merge
- ❌ Índice SQL v2.0 — no aplicado

## Próximos pasos (Sprint 3)

1. Aprobación índice SQL v2.0 + migración coordinada con `account_move.init()`.
2. Wizards NC/ND extendidos y retención B11 (con módulo pagos).
3. Despliegue controlado a clon `justech_dev` tras aprobación explícita.
