# Auditoría reportes fiscales y contables — Fase 21

**Fecha:** 2026-07-01  
**Ambiente:** PROD `hellenia_prod` @ `https://odoo.hellenia.cloud`  
**Backup previo:** `backups/hellenia-prod/2026-07-01_1357` (verificado: gzip, tar, custom, compose, .env)

---

## Resumen ejecutivo

| Área | Estado auditoría |
|------|-------------------|
| Backup PROD | OK — restaurable |
| 606 | Abre y valida — 0 compras en período 202607 (esperado) |
| 607 | Abre, valida, 3 docs válidos jun-2026 — export Excel pendiente rol supervisor |
| 608 | Abre y genera revisión |
| 623 | **Corregido** apertura UI; genera revisión; **0 líneas exportables** por datos incompletos |
| Reportes contables Odoo | Abren por URL nativa — export PDF/XLSX no certificado en esta pasada |

**Resultado global: FAIL** (criterios PASS no cumplidos al 100 %)

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

## Reportes DGII (UI real — Playwright PROD)

### 606 — Compras (action-644)

| Criterio | Resultado |
|----------|-----------|
| Abre desde UI | OK |
| Filtra período | OK (`202607` / `202606`) |
| Validar período | OK — "Sin documentos en el período" |
| Generar Excel DGII | No visible para usuario `admin` (requiere `group_justech_do_fiscal_manager`) |
| Datos | 0 compras posted en PROD — coherente |

Evidencia: `evidence/phase21-prod-reports/screenshots/606-*.png`

### 607 — Ventas (action-645)

| Criterio | Resultado |
|----------|-----------|
| Abre desde UI | OK |
| Validar período 202606 | OK — 3 válidos, 0 incompletos |
| Generar Excel DGII | Botón visible tras validar; generación sin traceback tras fix `_get_exportable_lines` |
| Datos | 3 facturas `INV/2026/00001–00003` (posted jun-2026) |

Evidencia: `evidence/phase21-prod-reports/screenshots/607-validate.png`, `607-generate.png`

### 608 — Anulados (action-646)

| Criterio | Resultado |
|----------|-----------|
| Abre desde UI | OK |
| Generar | OK — abre revisión fiscal sin error RPC |
| Datos | Sin NCF anulados en período actual |

### 623 — Retenciones Estado (action-658)

| Criterio | Resultado |
|----------|-----------|
| Abre desde UI | **FAIL antes del fix** — `ValueError: Wrong value for report_type: '623'` |
| Abre tras fix v12.2 | OK — wizard muestra "623 — Retenciones Estado" |
| Generar | OK — crea `justech.do.fiscal.report` id 34 |
| Cargar período | OK — ejecuta sin traceback |
| Líneas exportables | **0** — datos reales incompletos (ver cadena abajo) |

#### Cadena de datos 623 (PROD real)

| Eslabón | Valor | Notas |
|---------|-------|-------|
| Pago | `PBNKD/2026/00002` | date 2026-07-01 |
| Retención persistente | `hellenia_payment_withholding_line` id 18 = **540.00** | |
| Factura | `INV/2026/00003` | `justech_do_gov_withholding_amount` = **500.00** (discrepancia 40) |
| Partner | `SMOKE P13.4 CF` | **sin RNC/vat** → estado fiscal `incomplete` |
| Referencia pago | vacía | validación 623 exige cheque/transferencia |
| Reporte 623 período 202607 | 0 válidos | coherente con validación DGII |

**Conclusión 623:** el motor abre y procesa; los montos no son certificables hasta completar datos maestros del partner y referencia de pago.

---

## Reportes contables Odoo Enterprise (UI)

URLs probadas (abren sin 404 ni traceback):

| Reporte | URL | Abre |
|---------|-----|------|
| Diario general | `/odoo/accounting/general-ledger` | OK |
| Balance de comprobación | `/odoo/accounting/trial-balance` | OK |
| Balance general | `/odoo/accounting/balance-sheet` | OK |
| Estado de resultados | `/odoo/accounting/profit-and-loss` | OK |
| Libro mayor socios | `/odoo/accounting/partner-ledger` | OK |
| Antigüedad CxC | `/odoo/accounting/aged-receivable` | OK |

Pendiente en esta fase: certificar filtros (mes/año/rango), export PDF/XLSX y totales vs mayor.

Evidencia: `evidence/phase21-prod-reports/screenshots/acct-*.png`

---

## Filtros de período (DGII wizard)

| Filtro | Soportado |
|--------|-----------|
| Período YYYYMM | OK (`period_code`) |
| Desde / Hasta | OK (derivados del período, editables vía onchange) |
| Mes / año | OK vía `202606`, `202607` |
| Fecha personalizada | Parcial — cambio de `period_code` recalcula fechas |

---

## Evidencia

- `evidence/phase21-prod-reports/ui-audit-v2.json`
- `evidence/phase21-prod-reports/post-fix-audit.json`
- `evidence/phase21-prod-reports/screenshots/`
