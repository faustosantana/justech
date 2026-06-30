# Fase 19.1 — Validación real exportador 606 en TEST

**Fecha:** 2026-06-30  
**VPS:** `root@2.25.69.179` → `/opt/odoo-projects/hellenia`  
**Rama:** `cursor/phase19-fiscal-fields-606-dd85`  
**Base:** `phase18-3-withholding-certification`  
**Base de datos:** `hellenia_test` (solo TEST — sin PROD)

## Resultado ejecutivo

| Criterio | Estado |
|----------|--------|
| Backup TEST | PASS (`backups/test/2026-06-30_2132`) |
| Upgrade módulos | PASS |
| Validación funcional 19.1 (`run-phase19-1-test.sh`) | **PASS 31/31** |
| Excel 606 demo generado | PASS |
| Errores en español | PASS |
| Export período completo (wizard UI) | **BLOQUEADO** por data histórica UAT |
| Unit tests Odoo en `hellenia_test` | FAIL (colisión NCF con datos demo P19) |
| Listo para aprobación contable (subset demo) | **Sí, con reservas** |
| Avanzar a 607/608 | **No** hasta aprobación contable explícita |

## Evidencia

| Archivo | Ruta VPS | Repo |
|---------|----------|------|
| JSON | `/opt/odoo-projects/hellenia/evidence/phase19-606-test.json` | `evidence/phase19-606-test.json` |
| Excel | `/opt/odoo-projects/hellenia/evidence/phase19-606-export.xlsx` | `evidence/phase19-606-export.xlsx` |
| Log | `/opt/odoo-projects/hellenia/logs/phase19-1-test.log` | — |

## Ejecución en VPS

```bash
cd /opt/odoo-projects/hellenia
git fetch --all
git -C repository checkout cursor/phase19-fiscal-fields-606-dd85
git -C repository pull origin cursor/phase19-fiscal-fields-606-dd85
rsync -av repository/custom/ ./custom/
rsync -av repository/scripts/ ./scripts/

./scripts/backup-test.sh
./scripts/verify-backup-test.sh
bash scripts/update-custom-modules.sh test \
  justech_l10n_do_base justech_l10n_do_ncf hellenia_account justech_l10n_do_reports

bash scripts/run-phase19-1-test.sh
```

Menú UI: **Contabilidad → Reportes → Reportes DGII → Generar 606**

## Datos demo P19 creados en TEST

| Escenario | Ref | Partner | NCF |
|-----------|-----|---------|-----|
| Proveedor formal B11 | `P19-B11-ITBIS` | RNC 131793916 | B11… |
| Compra exenta | `P19-B11-EXEMPT` | Formal B11 | B11… |
| Retención ITBIS 30% | `P19-B11-WH-ITBIS30` | Formal B11 | B11… |
| Retención ISR 10% informal | `P19-B13-WH-ISR10` | Cédula 00112345678 | B13… |
| Varias retenciones | `P19-B13-MULTI-WH` | Informal B13 | B13… |
| Nota de crédito proveedor | `P19-B11-NC` | Formal B11 | B04… + `ncf_modified` |
| Pago parcial | `P19-B11-ITBIS` | — | estado `partial` |
| Pago total | `P19-B11-WH-ITBIS30` | — | estado `paid` |

## Validación Excel 606 (subset demo P19)

Checks PASS en evidencia JSON:

- Archivo `DGII_606_202606.xlsx` generado sin errores
- Encabezados fila 11: RNC/Cédula, NCF, Fecha, Monto, ITBIS, ITBIS retenido, ISR retenido, Forma de pago, Estatus (columnas A–AA)
- Datos desde fila 12 (6 líneas demo)
- RNC `131793916`, NCF `B1100000001`, fecha `20260630`, monto `1000`
- Historial fiscal (`justech.do.fiscal.report`) con adjunto Excel

## Validaciones de error en español

| Caso | Mensaje esperado | Estado |
|------|------------------|--------|
| Proveedor sin RNC | `no tiene RNC/Cédula` | PASS (data legacy + P19) |
| Factura sin NCF | `no tiene NCF` | PASS |
| Proveedor sin tipo id DGII | `no tiene tipo de identificación DGII` | PASS |
| Retención sin código DGII | `sin código DGII configurado` | PASS |
| Fecha fuera de período | sin facturas en 2020-01 | PASS |
| Impuesto no clasificado | `impuesto no clasificado para DGII` | Cubierto en unit tests |

## Hallazgos y errores corregidos durante 19.1

1. **PermissionError** al escribir evidencia en `/opt/odoo-projects` desde contenedor → volumen montado `/evidence` + `chmod 777`.
2. **NCF inválido** en script (10 chars) → formato 11 chars `B11` + 8 dígitos.
3. **UnboundLocalError `_`** en `validate_moves_606` (sombreado de traducción).
4. **Duplicados P19** en re-ejecuciones → `find_demo_move()` + refs explícitos `DEMO_REFS`.
5. **Pagos idempotentes** en re-ejecución TEST.
6. **Export período completo** bloqueado por ~216 facturas legacy UAT/Fase 4/5 sin RNC, tipo id o NCF — comportamiento esperado del validador estricto.

## Campos P1 aún no implementados (no bloquean demo)

Según `dgii_606_mapping.json`:

- `justech_do_expense_type_606` (columna D — tipo bienes/servicios DGII)
- `justech_do_payment_method_dgii` (columna Z — hoy se infiere de pagos)
- ITBIS proporcionalidad, costo, anticipos, ISC, propina legal, etc.

El exportador usa valores por defecto/heurísticas donde aplica.

## Unit tests Odoo

Los tests en `custom/justech_l10n_do_reports/tests/test_phase19_dgii_606.py` pasan en base limpia. En `hellenia_test` con datos P19 ya cargados pueden fallar por colisión de NCF (`B1100000001`). Ejecutar en DB de prueba aislada o tras limpieza de collisiones.

## Criterios PASS Fase 19.1

- [x] Backup y verificación TEST
- [x] Upgrade módulos Fase 19
- [x] Datos demo completos (B11, B13, ITBIS, exenta, retenciones, NC, pagos)
- [x] Excel 606 generado y validado
- [x] Errores en español
- [x] Evidencia `evidence/phase19-606-test.json`
- [x] Sin tocar PROD ni odoo-pecv

## Recomendación para contabilidad

**El exportador 606 es funcional para un conjunto de facturas válidas** (demostrado con subset P19). Para uso operativo en TEST con período completo:

1. Completar datos fiscales en proveedores/facturas legacy UAT, **o**
2. Exportar solo movimientos validados (filtro por refs / wizard con pre-validación), **o**
3. Limpiar/archivar data UAT obsoleta antes del cierre mensual.

**No promover a PROD** sin aprobación explícita del equipo contable.

**No iniciar 607/608/609/623** hasta que contabilidad apruebe el 606 y defina estrategia para data histórica.
