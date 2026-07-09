# Gate — Activación motor NCF Justech

**Fecha:** 2026-07-09  
**Estado Fase A reportes:** ✅ Cerrada (punto estable)  
**Motor NCF Justech:** ⛔ **BLOQUEADO** hasta completar ítems obligatorios

Este documento define qué debe estar **verificado y aprobado** antes de activar `justech_do_fiscal_enabled` o asignar NCF vía motor Justech en cualquier entorno operativo.

---

## Completado (no repetir)

| # | Ítem | Evidencia |
|---|------|-----------|
| ✅ | Fiscal Data Provider desplegado y validado | `FDP-deploy-20260709/` |
| ✅ | Reportes 606–609 leen vía FDP | `FISCAL_DATA_PROVIDER_REPORT.md` |
| ✅ | Clasificador DGII parametrizable `19.0.1.16.1` | `CLASSIFIER-closure-final/` |
| ✅ | 606/202606 = 0 errores en `justech_dev` | `CLOSURE_VALIDATE.json` |
| ✅ | Histórico intacto (2255/947/677/1504) | healthcheck + baseline |
| ✅ | Adel activo, Justech NCF motor OFF | `justech_dev` flags |
| ✅ | Lab NCF Fase 2 (duplicados, constraints v2.0) | `evidence/ncf-lab-phase2/` |

---

## Pendiente obligatorio antes de activar motor NCF Justech

### A. Infraestructura y entorno

| # | Ítem | Criterio de cierre | Prioridad |
|---|------|-------------------|-----------|
| A-1 | BD lab aislada `justech_ncf_lab` con clon validado | Backup verificado + healthcheck PASS | P0 |
| A-2 | Stack Docker lab separado de `justech_dev` | Puertos, redes, nombres distintos | P0 |
| A-3 | Procedimiento rollback NCF documentado y probado | Restore BD + filestore < 30 min | P0 |

### B. Motor NCF — funcionalidad mínima

| # | Ítem | Criterio de cierre | Prioridad |
|---|------|-------------------|-----------|
| B-1 | Rangos NCF DGII reales configurados por empresa | Rangos vigentes, no smoke | P0 |
| B-2 | Clave fiscal v2.0 (empresa+módulo+tipo+NCF+emisor) | Tests duplicado PASS en lab | P0 |
| B-3 | Emisión B01–B04 ventas en lab sin Adel write | Matriz fiscal lab 100% | P0 |
| B-4 | Recepción B11/B13/E41 compras en lab | Validación RNC proveedor | P0 |
| B-5 | NC/ND con NCF modificado y trazabilidad origen | E2E lab | P0 |
| B-6 | Modo coexistencia `parallel` documentado | Adel histórico + Justech solo docs nuevos | P0 |
| B-7 | Cron alertas agotamiento rangos | TD-019 | P1 |
| B-8 | B03 E2E + `in_refund` NCF (TD-011, TD-012) | Tests PASS | P1 |

### C. Migración histórico (sin tocar GL)

| # | Ítem | Criterio de cierre | Prioridad |
|---|------|-------------------|-----------|
| C-1 | Backfill metadatos 1.504 NCF → `justech_do_ncf` (modo `historical_import`) | 0 cambios en `account_move_line` balances | P0 |
| C-2 | Validación post-backfill: FDP devuelve misma NCF que Adel | Muestra 100% match | P0 |
| C-3 | Secuencia: instalar Justech → backfill → **luego** evaluar desinstalar Adel | Documentado en runbook | P0 |
| C-4 | Migración por empresa (PlugSafe → Omni → Just Office → JUSTECH) | Sign-off por empresa | P1 |

### D. Reportes y clasificación (extensión)

| # | Ítem | Criterio de cierre | Prioridad |
|---|------|-------------------|-----------|
| D-1 | 607/608/609 certificación volumen real (no solo período vacío) | QA + contador | P1 |
| D-2 | 623 retenciones Estado con datos reales | Volumen TEST/PROD piloto | P1 |
| D-3 | Catálogo clasificación revisado por contador (154 impuestos) | Sign-off matriz | P1 |
| D-4 | Desacople `hellenia.withholding.catalog` → módulo Justech genérico | Refactor C-04 | P2 |

### E. UX y operación

| # | Ítem | Criterio de cierre | Prioridad |
|---|------|-------------------|-----------|
| E-1 | Dashboard fiscal v1 (`justech_l10n_do_dashboard`) | Secuencias, alertas, home | P1 |
| E-2 | Wizard configuración inicial + asistente primera factura | UX Fase 3A | P1 |
| E-3 | Mensajes error NCF duplicado con detalle colisión | UX | P2 |

### F. Gobernanza y despliegue

| # | Ítem | Criterio de cierre | Prioridad |
|---|------|-------------------|-----------|
| F-1 | Merge `feature/fiscal-integration-phase-a` → `development` | Aprobación explícita propietario | P0 |
| F-2 | Despliegue controlado `erp.justech.do` post-merge | Backup + healthcheck + validación 606 | P0 |
| F-3 | Sign-off contador período 202606 exportable | Evidencia firmada | P0 |
| F-4 | **Producción `justgroup.app`** | Solo tras F-1..F-3 + ventana aprobada | P0 |

---

## Secuencia recomendada (no saltar pasos)

```
1. Merge rama fiscal (aprobación propietario)
2. Lab NCF: matriz B01–B15 + duplicados v2.0 (justech_ncf_lab)
3. Backfill metadatos histórico en lab (sin GL)
4. Piloto parallel mode en justech_dev (1 empresa, docs NUEVOS solo)
5. Certificación 607/623 volumen
6. Sign-off contador
7. Activar motor NCF por empresa (PlugSafe → … → JUSTECH)
8. Producción — solo con ventana controlada
```

---

## Criterio de activación del motor (definición)

Se podrá activar `justech_do_fiscal_enabled = True` en una empresa cuando:

1. **A-1..A-3** y **B-1..B-6** cerrados en lab.
2. **C-1..C-2** validados en lab (backfill sin GL).
3. **F-1..F-3** aprobados para el entorno destino.
4. Rollback probado en las últimas 72 h.
5. Adel permanece activo en modo `parallel` hasta sign-off de cutover por empresa.

**Prohibido:** activar motor NCF en `justgroup.app` antes de todos los ítems P0.
