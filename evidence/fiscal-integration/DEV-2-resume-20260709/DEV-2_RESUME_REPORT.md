# DEV-2 Resume — Stack fiscal Justech en justech_dev

| Campo | Valor |
|-------|-------|
| **Fecha** | 2026-07-09 |
| **Entorno** | `erp.justech.do` / BD `justech_dev` |
| **Rollback** | `/opt/odoo-dev/backups/fiscal-integration-stabilized-20260709_222306` |
| **Resultado** | **PASS** |

## Módulos instalados

| Módulo | Versión | Estado |
|--------|---------|--------|
| `l10n_do_accounting` (Adel) | 19.0.1.0.0 | ✅ activo — motor facturación |
| `justech_l10n_do_base` | 19.0.1.6.0 | ✅ installed |
| `justech_l10n_do_ncf` | 19.0.2.1.0 | ✅ installed, **inactivo** |
| `justech_l10n_do_reports` | 19.0.1.14.0 | ✅ installed |

| Control coexistencia | Valor |
|---------------------|-------|
| `justech_do_fiscal_enabled` | **false** en 4 empresas |
| Diarios `justech_do_use_ncf` | **0** |
| NCF Justech posted | **0** |

## Healthcheck

| Fase | Resultado |
|------|-----------|
| Pre-DEV-2 | ✅ 18/18 PASS |
| Post-DEV-2 | ✅ 18/18 PASS |

## 606/607 (solo lectura)

| Métrica | Valor |
|---------|-------|
| Movimientos elegibles 606 | 763 |
| Movimientos elegibles 607 | 741 |
| Exporters 606/607 | ✅ |
| Wizard 606/607 | ✅ instanciable |
| Reportes generados | 0 (smoke no escribe) |

## Comparativa antes / después

| Métrica | Pre | Post | Δ |
|---------|:---:|:----:|:-:|
| Asientos posted | 2.255 | 2.255 | 0 |
| NCF Adel | 1.504 | 1.504 | 0 |
| NCF Justech posted | 0 | 0 | 0 |
| Conciliaciones | 947 | 947 | 0 |
| Pagos activos | 677 | 677 | 0 |
| GL balanceado | ✅ | ✅ | — |
| Empresas fiscal ON | 0 | 0 | 0 |

## Validaciones ejecutadas

| Validación | Resultado |
|------------|-----------|
| Adel activo | ✅ |
| Facturas históricas (5) | ✅ |
| Borrador factura (rollback savepoint) | ✅ id=3922 |
| Pagos (5) | ✅ |
| Conciliaciones (5 líneas) | ✅ |
| NC posted (3) | ✅ |
| Secuencias / campos Adel | ✅ |
| Assets físicos 149/149 | ✅ |
| Assets HTTP 200 | ✅ |
| Login | ✅ (healthcheck) |
| Ventas / contabilidad | ✅ |
| Sin menús fiscales para vendedor | ✅ |
| validate_full 19 checks | ✅ pre + post |

## Acción ejecutada

- Sync código `base`, `ncf`, `reports` desde repo
- Upgrade `-u justech_l10n_do_base,justech_l10n_do_ncf,justech_l10n_do_reports`
- SQL `justech_do_fiscal_enabled = false` en 4 empresas
- **Sin** `mv` filestore
- **Sin** rollback (upgrade limpio)

## Riesgos

| ID | Riesgo | Severidad | Estado |
|----|--------|-----------|--------|
| R1 | Activación accidental Justech NCF | Alta | Mitigado (SQL post-upgrade) |
| R2 | Coexistencia Adel + Justech `_post` | Media | Mitigado (fiscal OFF) |
| R3 | 623 sin `hellenia_account` | Baja | No probado generación |
| R4 | Scripts lab con `mv` filestore | Alta | Documentado — prohibido |

## Rollback disponible

```
/opt/odoo-dev/backups/fiscal-integration-stabilized-20260709_222306
```

Procedimiento automático en `scripts/fiscal-integration-dev2-resume.sh` (función `rollback_now`).

## Evidencias

`evidence/fiscal-integration/DEV-2-resume-20260709/`  
Servidor: `/opt/odoo-dev/evidence/fiscal-integration/DEV-2-resume-20260709_224749/`

## Restricciones respetadas

- ❌ justgroup.app
- ❌ Desinstalar Adel
- ❌ Activar motor NCF Justech
- ❌ Modificar histórico / pagos / conciliaciones / asientos
- ❌ `mv` filestore
- ❌ merge development/main

## Siguiente paso recomendado (DEV-3)

1. Generar **606/607** de un periodo cerrado (export TXT, sin envío DGII).
2. Piloto **1 empresa** con rangos NCF Justech + `justech_do_fiscal_enabled=true` (Adel en las otras 3).
3. Evaluar `hellenia_account` si se requiere formato 623 completo.
