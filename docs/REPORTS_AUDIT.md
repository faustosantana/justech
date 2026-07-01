# Auditoría reportes fiscales y contables — Fase 21

**Fecha:** 2026-07-01 (actualización final pasada)  
**Ambiente:** PROD `hellenia_prod` @ `https://odoo.hellenia.cloud`  
**Módulo reportes:** `justech_l10n_do_reports` 19.0.1.12.2  
**Backup previo:** `backups/hellenia-prod/2026-07-01_1357` (verificado: gzip, tar, custom, compose, .env)

---

## Resumen ejecutivo

| Área | Estado auditoría |
|------|-------------------|
| Backup PROD | OK — restaurable |
| 606 | Abre, valida, genera — 0 compras en período (esperado) |
| 607 | Abre, valida 3 docs jun-2026, genera sin RPC — export programático OK |
| 608 | Abre y genera revisión fiscal |
| 623 | Abre y genera tras fix v12.2; **0 líneas exportables** — datos incompletos |
| Reportes contables Odoo | Abren desde UI; botones PDF/XLSX visibles; totales YTD cuadran |
| Regresión pagos/retenciones | No ejecutada en esta pasada |

**Resultado global: FAIL** (criterios PASS completos no cumplidos)

---

## Backup PROD (2026-07-01_1357)

| Artefacto | Tamaño | Verificación |
|-----------|--------|--------------|
| `postgres_all.sql.gz` | 3.5 MB | `gunzip -t` OK |
| `filestore.tar.gz` | 4.4 MB | `tar -tzf` OK |
| `custom.tar.gz` | 150 KB | OK |
| `docker-compose.yml` | OK | |
| `.env` | OK | |
| `odoo.conf` | OK | |
| Contiene `hellenia_prod` | OK | |

---

## Matriz funcional por reporte

Leyenda: ✅ OK | ⚠️ Parcial | ❌ FAIL | — No aplica

### Reportes DGII

| Reporte | Abre UI | Filtra | Exporta | PDF | XLSX | Datos | Totales | Estado |
|---------|---------|--------|---------|-----|------|-------|---------|--------|
| 606 | ✅ | ✅ | ⚠️ | — | ⚠️ | ✅ (0 docs) | ✅ | Parcial |
| 607 | ✅ | ✅ | ✅ | — | ⚠️ | ✅ (3 docs) | ⚠️ | Parcial |
| 608 | ✅ | ✅ | ✅ | — | — | ✅ (0 anulados) | ✅ | Parcial |
| 623 | ✅ | ✅ | ✅ revisión | — | ⚠️ | ❌ | ❌ | **FAIL** |

### Reportes contables

| Reporte | Abre UI | Filtra | Exporta | PDF btn | XLSX btn | Datos | Totales | Estado |
|---------|---------|--------|---------|---------|----------|-------|---------|--------|
| Diario general | ✅ | ⚠️ | ⚠️ | ✅ | ✅ | ⚠️ | ⚠️ | Parcial |
| Mayor general | ✅ | ⚠️ | ⚠️ | ✅ | ✅ | ⚠️ | ⚠️ | Parcial |
| Balance comprobación | ✅ | ⚠️ | ⚠️ | ✅ | ✅ | ✅ SQL | ✅ | Parcial |
| Balance general | ✅ | ⚠️ | ⚠️ | ✅ | ✅ | ⚠️ | ⚠️ | Parcial |
| Estado resultados | ✅ | ⚠️ | ⚠️ | ✅ | ✅ | ⚠️ | ⚠️ | Parcial |
| Auxiliar clientes | ✅ | ⚠️ | ⚠️ | ✅ | ✅ | ⚠️ | ⚠️ | Parcial |
| Auxiliar proveedores | — | — | — | — | — | — | — | Pendiente URL |
| Antigüedad CxC | ✅ | ⚠️ | ⚠️ | ✅ | ✅ | ⚠️ | ⚠️ | Parcial |
| Libro diario | ✅ | ⚠️ | ⚠️ | ✅ | ✅ | ⚠️ | ⚠️ | Parcial |

---

## Reportes DGII (UI real — Playwright PROD)

### 606 — Compras (action-644)

| Criterio | Resultado |
|----------|-----------|
| Abre desde UI | OK |
| Validar período 202606 | OK — sin documentos |
| Generar | OK — sin traceback |
| Datos | 0 compras posted en PROD — coherente |

Evidencia: `evidence/phase21-prod-reports/screenshots/dgii-606-*.png`

### 607 — Ventas (action-645)

| Criterio | Resultado |
|----------|-----------|
| Abre desde UI | OK |
| Validar período 202606 | OK — 3 válidos |
| Generar Excel DGII | OK — sin RPC tras fix `_get_exportable_lines` |
| Export programático | OK — `action_export_dgii` en odoo shell |
| Datos | `INV/2026/00001`, `00002`, `00003` (posted jun-2026) |

Evidencia: `evidence/phase21-prod-reports/screenshots/dgii-607-*.png`

### 608 — Anulados (action-646)

| Criterio | Resultado |
|----------|-----------|
| Abre desde UI | OK |
| Generar | OK — revisión fiscal id 41 |
| Datos | Sin NCF anulados en período |

### 623 — Retenciones Estado (action-658)

| Criterio | Resultado |
|----------|-----------|
| Abre desde UI | OK tras fix v12.2 (antes: `ValueError: Wrong value for report_type: '623'`) |
| Generar | OK — revisión fiscal id 42 |
| Cargar período 202607 | OK — sin traceback |
| Líneas exportables | **0** — validación DGII rechaza datos |

#### Cadena de datos 623 (PROD real — SQL + odoo shell)

| Eslabón | Valor | Notas |
|---------|-------|-------|
| Pago | `PBNKD/2026/00002` (id 72) | fecha 2026-07-01, state=paid |
| Retención persistente | línea id **18** = **540.00** | catálogo **RET-ITBIS-30** (`affects_623=false`) |
| Línea contable | `account_move_line` id **354** | débito **540.00** — coincide con retención |
| Factura | `INV/2026/00003` (id 25) | `justech_do_gov_withholding_amount` = **500.00** |
| Partner | id **23** `SMOKE P13.4 CF` | **sin RNC/vat** → `incomplete` |
| Referencia pago | vacía | fallback `payment.name` disponible en exportador |
| Validación jul-2026 | 0 válidos, 2 incompletos | error: falta RNC |

**Discrepancia montos:** retención contable 540 (ITBIS 30%) vs campo gobierno en factura 500. No certificable sin alinear datos de prueba.

**Conclusión 623:** motor operativo; falla certificación por **datos maestros** (RNC) y **inconsistencia** retención ITBIS vs monto gobierno en factura.

---

## Reportes contables Odoo Enterprise (UI)

Auditoría Playwright 2026-07-01T14:12 UTC — todos abren sin RPC:

| Reporte | URL | Abre | PDF | XLSX |
|---------|-----|------|-----|------|
| Diario general | `/odoo/accounting/general-ledger` | OK | OK | OK |
| Balance comprobación | `/odoo/accounting/trial-balance` | OK | OK | OK |
| Balance general | `/odoo/accounting/balance-sheet` | OK | OK | OK |
| Estado resultados | `/odoo/accounting/profit-and-loss` | OK | OK | OK |
| Auxiliar socios | `/odoo/accounting/partner-ledger` | OK | OK | OK |
| Antigüedad CxC | `/odoo/accounting/aged-receivable` | OK | OK | OK |
| Libro diario | `/odoo/accounting/journal-report` | OK | OK | OK |

### Validación contable SQL (YTD 2026)

| Métrica | Valor | Estado |
|---------|-------|--------|
| Asientos posted revisados | 7 | OK balanceados |
| Suma débitos YTD | 70,800.00 | |
| Suma créditos YTD | 70,800.00 | OK cuadra |

Pendiente: descarga real PDF/XLSX, filtros mes/año/rango personalizado, auxiliar proveedores.

---

## Filtros de período (DGII wizard)

| Filtro | Soportado |
|--------|-----------|
| Período YYYYMM | OK (`period_code`) |
| Desde / Hasta | OK (derivados del período) |
| Mes / año | OK vía `202606`, `202607` |
| Fecha personalizada | Parcial — `period_code` recalcula fechas vía onchange |

---

## Evidencia

| Archivo | Descripción |
|---------|-------------|
| `evidence/phase21-prod-reports/ui-audit-full.json` | Auditoría UI completa post-fix |
| `evidence/phase21-prod-reports/prod-data-audit-parsed.json` | Validación odoo shell |
| `evidence/phase21-prod-reports/screenshots/` | Capturas UI |
| `scripts/phase21-prod-ui-audit.py` | Script Playwright |
| `scripts/phase21-prod-data-audit.py` | Script odoo shell |
