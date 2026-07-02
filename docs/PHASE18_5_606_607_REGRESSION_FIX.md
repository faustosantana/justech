# Fase 18.5 — Cierre regresión 606/607 antes de producción

**Ambiente:** TEST (`hellenia_test` @ `test.hellenia.cloud`)  
**VPS:** `root@2.25.69.179` → `/opt/odoo-projects/hellenia`  
**Módulo retenciones:** `hellenia_account` **19.0.1.0.9**  
**Fecha validación:** 2026-07-01 UTC  
**Resultado:** **TEST PASS — regresión 100% PASS**

---

## Objetivo

Cerrar el único fallo restante de regresión (validación de fechas de período en reportes DGII 606/607) antes de solicitar aprobación para promover el motor de retenciones a producción.

**Restricciones respetadas:** no se tocó producción ni `odoo-pecv`.

---

## Causa exacta del fallo 606/607

Los scripts de regresión `phase18-validate-withholding-test.py`, `phase18-2-validate-withholding-catalog-test.py` y `phase18-3-certify-withholding-test.py` creaban reportes fiscales con:

```python
date_from = date.today().replace(month=1, day=1)  # 1 enero (YTD)
date_to = date.today()                             # hoy
```

sin pasar un `period_code` coherente. Esto provocaba **dos fallos encadenados**:

### 1. Wizard (`justech.do.fiscal.report.wizard`)

- `period_code` por defecto = mes actual (`202607` en julio 2026).
- `validate_period_dates()` compara fechas contra los límites del período YYYYMM.
- Rango YTD `2026-01-01 — 2026-07-01` **no coincide** con período `202607` (esperado `2026-07-01 — 2026-07-31`).
- Error: *"Las fechas … no coinciden con el período 202607"*.

### 2. Modelo `justech.do.fiscal.report`

- Si solo se pasan fechas, `period_code` se deriva de `date_from` → enero (`202601`).
- `_sync_dates_from_period_code()` reduce el rango a **solo enero**.
- Facturas con `invoice_date = hoy` quedan **fuera del rango** del reporte.
- Resultado: `lines606 = False`, `lines607 = False` en certificación 18.3.

**No era un bug de lógica de producto** en fechas de factura, contable, pago, zona horaria ni filtro del reporte. Era un **anti-patrón en los scripts de prueba**: rango acumulado año-a-fecha (YTD) incompatible con el modelo fiscal DGII de período mensual `YYYYMM`.

---

## Corrección aplicada

### Scripts de regresión (TEST)

Se añadió helper `_dgii_period()` en los tres scripts afectados y en el nuevo validador 18.5:

```python
def _dgii_period():
    util = env["justech.do.dgii.period"]
    code = util.default_period_code()
    date_from, date_to = util.period_bounds_from_code(code)
    return code, date_from, date_to
```

Al crear wizard y `fiscal.report` se pasa explícitamente:

- `period_code` = mes actual (`YYYYMM`)
- `date_from` / `date_to` = primer y último día del mes
- alineado con `invoice_date = date.today()` de las facturas de prueba

### Orquestador de regresión

- Nuevo `scripts/phase18-5-regression-test.py` — valida período mensual, rechazo del patrón YTD, wizard 606/607 y generación con facturas del mes.
- Nuevo `scripts/run-phase18-5-regression-test.sh` — ejecuta fases 18, 18.2, 18.3, 18.4 y 18.5 en `hellenia_test`.
- Corrección del agregador JSON: parser multilínea con `json.JSONDecoder().raw_decode()` (los scripts 18/18.2/18.3 emiten JSON indentado).

**Sin cambios en código de producto** para esta fase; la lógica DGII en `justech.do.dgii.period` y `fiscal_report_wizard` ya era correcta.

---

## Reejecución regresión completa (TEST)

| Fase | Script | Resultado | Detalle |
|------|--------|-----------|---------|
| 18 | `phase18-validate-withholding-test.py` | **PASS** | 18/18 tests — pagos cliente/proveedor, 606, 607, asientos, conciliación |
| 18.2 | `phase18-2-validate-withholding-catalog-test.py` | **PASS** | 23/23 tests — catálogo, pagos, 606, 607, asientos |
| 18.3 | `phase18-3-certify-withholding-test.py` | **PASS** | 23/23 checks — certificación integral incl. `17_reports_606_607` |
| 18.4 | `phase18-4-withholding-calculation-test.py` | **PASS** | 19/19 checks — ITBIS 30%, 75%, 100% |
| 18.5 | `phase18-5-regression-test.py` | **PASS** | 13/13 checks — período, wizard 606/607, reportes con facturas |

**Agregado:** `evidence/phase18-5-regression-test.json` → `all_pass: true`

### Cobertura por área solicitada

| Área | Cubierto en |
|------|-------------|
| 606 | Fase 18 (`10_report_606`), 18.2 (`17_report_606`), 18.3 (`17_reports_606_607`), 18.5 (wizard + report) |
| 607 | Fase 18 (`11_report_607`), 18.2 (`18_report_607`), 18.3 (`17_reports_606_607`), 18.5 (wizard + report) |
| Pagos cliente | Fase 18, 18.2, 18.3, 18.4 |
| Pagos proveedor | Fase 18, 18.2, 18.3, 18.4 |
| Asientos | Fase 18 (`12_balanced_entry`), 18.2 (`13_balanced_entry`), 18.3 (`13-15`) |
| Conciliaciones | Fase 18 (`13_reconciliation_ready`), 18.3 (`16_bank_reconciliation_ready`) |

---

## Evidencia

- Consolidado: `evidence/phase18-5-regression-test.json`
- Detalle por fase en VPS: `evidence/phase18-regression-18*.json`
- Log: `logs/deploy/phase18-5-regression-2026-07-01_*.log`

Comando de revalidación:

```bash
cd /opt/odoo-projects/hellenia
bash scripts/run-phase18-5-regression-test.sh
```

---

## Conclusión

| Pregunta | Respuesta |
|----------|-----------|
| **TEST PASS / FAIL** | **PASS** |
| **Causa 606/607** | Scripts usaban rango YTD sin `period_code` coherente → validación de período fallaba y facturas de hoy quedaban fuera del reporte |
| **Corrección** | Período mensual DGII (`period_code` + `period_bounds_from_code`) en scripts de regresión |
| **Regresión 100% PASS** | **Sí** — fases 18, 18.2, 18.3, 18.4, 18.5 |
| **Listo para pedir aprobación de promoción** | **Sí** — no quedan FAIL de regresión en TEST. Promoción a producción **requiere aprobación explícita**; no se ha promovido. |
