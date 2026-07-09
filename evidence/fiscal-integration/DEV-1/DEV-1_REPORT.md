# Iteración DEV-1 — Integración real erp.justech.do

| Campo | Valor |
|-------|-------|
| **Iteración** | DEV-1 (Integración erp.justech.do #1) |
| **Fecha** | 2026-07-09 |
| **BD** | `justech_dev` @ erp.justech.do |
| **Backup** | `/opt/odoo-dev/backups/fiscal-integration-dev1-20260709_214432` |
| **Restauración validada** | ✅ `RESTORE_VALIDATE_OK` |
| **Resultado** | **PASS** |

## Componentes instalados

| Módulo | Versión | Estado |
|--------|---------|--------|
| `justech_l10n_do_base` | 19.0.1.6.0 | ✅ installed |
| `justech_l10n_do_ncf` | 19.0.2.1.0 | ✅ installed |

## Coexistencia Adel (obligatorio)

| Control | Valor |
|---------|-------|
| `l10n_do_accounting` (Adel) | ✅ Sigue activo |
| `justech_do_fiscal_enabled` | **false** en 4 empresas |
| `justech_do_use_ncf` journals | **0** |
| NCF histórico Adel | **1.504** sin cambio |
| NCF Justech posted | **0** (esperado) |

> Justech NCF **instalado pero inactivo** — Adel sigue siendo el motor de emisión hasta iteración futura con cutover por empresa.

## Comparativa antes / después

| Métrica | Pre (backup) | Post | Δ |
|---------|:------------:|:----:|:-:|
| Asientos posted | 2.255 | 2.255 | 0 |
| NCF Adel | 1.504 | 1.504 | 0 |
| GL balanceado | ✅ | ✅ | — |
| Conciliaciones | 947 | 947 | 0 |
| Pagos activos | 677 | 677 | 0 |
| Empresas | 4 | 4 | 0 |

## Validaciones obligatorias

| Validación | Resultado |
|------------|-----------|
| Apertura factura histórica (ORM) | ✅ |
| Apertura pago | ✅ |
| Conciliaciones existentes | ✅ |
| Cliente / proveedor | ✅ |
| NC posted (muestra) | ✅ |
| Secuencias Adel | ✅ Sin cambio |
| Multiempresa (4) | ✅ |
| GL débito = crédito | ✅ |

## Componentes pendientes (próximas iteraciones)

| Componente | Motivo |
|------------|--------|
| `justech_l10n_do_reports` | Iteración DEV-2 |
| `justech_l10n_do_dashboard` | Shell — no prioritario |
| Activación Justech NCF por empresa | Requiere rangos + cutover planificado |
| Desinstalación Adel | Solo tras UAT completo |

## Riesgos encontrados

| ID | Riesgo | Severidad | Mitigación aplicada |
|----|--------|-----------|---------------------|
| R1 | Default `justech_do_fiscal_enabled=True` activa Justech al instalar | **Alta** | SQL force false post-install |
| R2 | Coexistencia doble `_post` Adel + Justech | Media | Fiscal disabled → assign skip |
| R3 | ORM `write()` no persistió flag en shell | Media | Install script usa SQL directo |

## Recomendación DEV-2

1. Instalar `justech_l10n_do_reports` tras backup incremental.
2. Ejecutar tests reports en lab; smoke read-only en dev.
3. Piloto **1 empresa** con `justech_do_fiscal_enabled=true` + rangos — sin desinstalar Adel en las otras 3.

## Rollback

Ver `rollback.md` y `BACKUP_PATH.txt` en backup del servidor.

## Restricciones respetadas

- ❌ justgroup.app
- ❌ Repost / modificar pagos / conciliaciones / histórico
- ❌ Merge development/main
