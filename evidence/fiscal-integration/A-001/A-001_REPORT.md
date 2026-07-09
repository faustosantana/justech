# Iteración A-001 — Baseline integración erp.justech.do

| Campo | Valor |
|-------|-------|
| **Iteración** | A-001 |
| **Fecha** | 2026-07-09 |
| **Entorno** | erp.justech.do |
| **Rama** | `feature/fiscal-integration-phase-a` |
| **Resultado** | **PASS** |

## Objetivo

Establecer baseline read-only del entorno operativo (`justech_dev`) y validar stack Justech en lab (`justech_ncf_lab`) sin modificar histórico.

## Declaración 8 puntos

| # | Punto | Respuesta |
|---|-------|-----------|
| 1 | Qué | Baseline audit + tests NCF + integridad GL/pagos/conciliaciones |
| 2 | Por qué | Punto de partida Fase A antes de integrar en entorno actual |
| 3 | Riesgos | Bajo — solo lectura en `justech_dev`; tests en lab aislado |
| 4 | Backup | No requerido (read-only dev; lab ya clon) |
| 5 | Rollback | N/A iteración documental + re-run scripts |
| 6 | Archivos | scripts A-001, docs FISCAL_INTEGRATION_PHASE_A, evidence/A-001 |
| 7 | Módulos | `justech_l10n_do_ncf` 19.0.2.1.0 (validación) |
| 8 | Tiempo | ~2h |

## Hallazgos clave

### justech_dev (operativo erp.justech.do)

| Métrica | Valor |
|---------|-------|
| Stack | **Adel** `l10n_do_accounting` 19.0.1.0.0 |
| Justech fiscal | **No instalado** |
| Posted moves | 2.255 |
| NCF Adel | 1.504 |
| NCF Justech | 0 |
| GL balanceado | ✅ |
| Conciliaciones | 947 |
| Pagos activos | 677 |
| Empresas | 4 |

### justech_ncf_lab (lab integración)

| Métrica | Valor |
|---------|-------|
| Stack | **Justech** base + ncf 19.0.2.1.0 + dashboard |
| Adel accounting | Desinstalado |
| hellenia_account | Instalado |
| justech_l10n_do_reports | **Pendiente** (siguiente iteración) |
| Posted moves | 2.255 (igual — histórico intacto) |
| NCF Justech | 1.494 |
| GL balanceado | ✅ |
| Conciliaciones | 947 |
| Pagos activos | 677 |

## Pruebas

```
justech_l10n_do_ncf: 31 post-tests — 0 failed, 0 errors
```

## Conclusión

- Histórico **intacto** en lab (mismos totales GL, pagos, conciliaciones).
- Entorno operativo **sin cambios** — Adel sigue activo en `justech_dev`.
- Lab demuestra stack Justech estable sobre clon histórico.
- **Brecha A-002:** instalar y validar `justech_l10n_do_reports` en lab.

## Restricciones respetadas

- ❌ justgroup.app
- ❌ Modificación histórico / repost / pagos / conciliaciones
- ❌ Merge

## Aprobación solicitada

Confirmar A-001 para proceder a **A-002** (reports en lab).
