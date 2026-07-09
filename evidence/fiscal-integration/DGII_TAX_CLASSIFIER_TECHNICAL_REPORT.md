# Informe Técnico — Motor de Clasificación Fiscal DGII (Justech)

**Fecha:** 2026-07-09  
**Entorno:** `erp.justech.do` / BD `justech_dev`  
**Rama:** `feature/fiscal-integration-phase-a`  
**Módulo:** `justech_l10n_do_reports` **19.0.1.16.1**  
**Evidencia cierre:** `evidence/fiscal-integration/CLASSIFIER-closure-final/`  
**Validación:** `CLOSURE_VALIDATE.json` — **28/28 checks PASS**

---

## 1. Objetivo

Construir el **motor de clasificación fiscal definitivo** del estándar Justech: eliminar toda lógica basada en nombres de impuestos (`"ISC" in tax.name`, `"ITBIS" in name`, etc.) y resolver columnas DGII exclusivamente mediante un **catálogo parametrizable**.

A partir de este diseño, un nuevo impuesto DGII se incorpora **agregando una fila al catálogo**, sin modificar código del exportador.

---

## 2. Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                    justech.do.fiscal.data.provider              │
│  (NCF, partner, tipos ingreso/gasto, exclusiones, anulados)     │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│              justech.do.dgii.tax.classification                 │
│  Catálogo: tax_id → rol fiscal → columnas 606/607/609           │
│  UI: Contabilidad → Reportes DGII → Clasificación fiscal        │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│              justech.do.dgii.tax.classifier (servicio)          │
│  • get_classification(tax)                                      │
│  • get_column(tax, report_code)                                 │
│  • move_column_amounts(move, report_code) → {N,W,X,Y...}        │
│  • unknown_taxes(move, report_code)                             │
│  • apply_tax_columns(row, move, report_code, sign)              │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
   606 exporter         607 exporter        608/609/623
   (compras)            (ventas)            (sin tax name logic)
```

### Componentes nuevos

| Componente | Archivo | Responsabilidad |
|---|---|---|
| Catálogo | `models/dgii_tax_classification.py` | Tabla `justech.do.dgii.tax.classification` |
| Clasificador | `models/dgii_tax_classifier.py` | Servicio abstracto, único punto de resolución |
| Migración | `migrations/19.0.1.16.0/post-migrate.py` | Sincroniza catálogo en upgrade |
| UI | `views/dgii_tax_classification_views.xml` | Mantenimiento parametrizable |
| Matriz FASE 1 | `scripts/fiscal-tax-matrix-analyze.py` | Análisis read-only de impuestos |

### Roles fiscales y columnas por defecto

| Rol | 606 | 607 | Uso |
|---|---|---|---|
| `itbis` | N | J | ITBIS facturado |
| `isc` | W | O | Impuesto Selectivo al Consumo |
| `other_tax` | X | P | Otros impuestos/tasas (CDT, telco, etc.) |
| `legal_tip` | Y | Q | Propina legal |
| `exempt` | — | — | Exento, sin columna |
| `ignore` | — | — | Retenciones negativas / no validar |

**Retenciones (ITBIS/ISR):** siguen resolviéndose vía `hellenia.withholding.catalog` (ya parametrizado). El clasificador no usa nombres de impuesto.

### Regla de diseño

Los exportadores **606** y **607** ya no contienen:
- `if "ISC" in tax.name`
- `_dgii_is_itbis_tax()` por nombre o tasa
- Comparaciones de texto contra `tax.name`

La validación llama `classifier.unknown_taxes(move, report_code)`.  
La exportación llama `classifier.apply_tax_columns(...)` para poblar N/W/X/Y (606) y J/O/P/Q (607).

---

## 3. FASE 1 — Matriz de impuestos (solo lectura)

**Script:** `scripts/fiscal-tax-matrix-analyze.py`  
**Evidencia:** `TAX_MATRIX_20260709.json`

### Resumen global (`justech_dev`)

| Métrica | Valor |
|---|---|
| Total impuestos | 154 |
| Purchase | 121 |
| Sale | 25 |
| Monto negativo (retenciones) | 53 |
| Con uso histórico posted | 15 |
| Sin clasificación legacy | 12 |

### Impuestos críticos del caso CDT (empresa JUSTECH)

| ID | Nombre | Tipo | Grupo | Cuenta | Empresas | Mov. históricos | Legacy | Recomendado |
|---|---|---|---|---|---|---|---|---|
| 5 | 18% ITBIS | purchase | ITBIS | — | JUSTECH | alto | 606_N | N / rol `itbis` |
| 14 | 10% ISC | purchase | ISC | 61020200 | JUSTECH | 34 líneas tax | 606_W (nombre) | W / rol `isc` |
| 15 | 2% CDT | purchase | Otros Impuestos | 61020200 | JUSTECH | 34 líneas tax | **ERROR legacy** | **X / rol `other_tax`** |
| 6 | 16% ITBIS | purchase | ITBIS | — | JUSTECH | — | 606_N | N |
| 7 | 9% ITBIS | purchase | ITBIS | — | — | — | 606_N | N |

La matriz completa (154 filas) está en `TAX_MATRIX_20260709.json`.

---

## 4. FASE 2 — Catálogo de clasificación

Modelo `justech.do.dgii.tax.classification`:

- `tax_id` (único, obligatorio)
- `classification_role` (itbis / isc / other_tax / legal_tip / exempt / ignore)
- `column_606`, `column_607`, `column_609` (parametrizables; sobreescriben defaults)
- `sync_from_taxes()` — crea entradas faltantes sin tocar las existentes

**Sincronización inicial:** 154 clasificaciones creadas para todos los `account.tax` activos/inactivos.

---

## 5. FASE 3 — Cambios en exportadores

### Archivos modificados

- `models/dgii_tax_classification.py` *(nuevo)*
- `models/dgii_tax_classifier.py` *(nuevo)*
- `models/dgii_606_exporter.py` — validación + columnas vía clasificador
- `models/dgii_607_exporter.py` — idem
- `models/dgii_exporter_mixin.py` — `_classifier()`, eliminado hook `_dgii_is_itbis_tax`
- `models/fiscal_report.py` — ITBIS vía clasificador
- `models/dgii_608_exporter.py`, `dgii_609_exporter.py`, `dgii_623_exporter.py` — limpieza hooks
- `hooks.py`, `migrations/19.0.1.16.0/post-migrate.py`
- `views/dgii_tax_classification_views.xml`
- `security/ir.model.access.csv`
- `__manifest__.py` → `19.0.1.16.0`

### Lo que NO se modificó (cumplimiento de reglas)

- Facturas, impuestos, histórico, pagos, conciliaciones, asientos, NCF, secuencias
- `justgroup.app` (producción)
- Motor NCF Justech (permanece OFF)
- Sin merge a `development` / `main`

---

## 6. FASE 4 — Validación reportes 606–609–623

**Período:** 202606 | **Empresa:** JUSTECH S.R.L. (id=1)

| Reporte | Documentos | Válidos | Errores | Clasificador | FDP |
|---|---|---|---|---|---|
| **606** | 90 | **90** | **0** | ✅ | ✅ |
| **607** | 74 | **74** | **0** | ✅ | ✅ |
| **608** | 0 | 0 | 0 | ✅ | ✅ |
| **609** | 0 | 0 | 0 | ✅ | ✅ |
| **623** | 0 | 0 | ✅ (hotfix `move_id`) | ✅ | ✅ |

> **623:** corregido `KeyError: move_id` en `classify_moves` — `_persistent_gov_lines` devolvía `account.move` vacío cuando el modelo withholding no estaba disponible; ahora valida `_name` antes de `.mapped("move_id")`.

---

## 6b. Cierre limpio — 10 verificaciones (2026-07-09)

| # | Verificación | Resultado |
|---|---|---|
| 1 | Catálogo persistido en BD post-upgrade | ✅ 154 filas (`post_catalog_persist.json`) |
| 2 | Sin scripts manuales para operar | ✅ Solo `-u justech_l10n_do_reports` |
| 3 | `post_init_hook` + `migration` + `sync` | ✅ `19.0.1.16.0` + `19.0.1.16.1/post-migrate.py` |
| 4 | 606 sin lógica por nombre | ✅ `exporters_no_name_logic` PASS |
| 5 | 607/608/609/623 no rotos | ✅ Todos ejecutan sin excepción |
| 6 | Histórico intacto | ✅ 2255/947/677/1504 NCF |
| 7 | 5 facturas CDT → columna X | ✅ FP/0083–0084, 0044–0046 |
| 8 | ISC → columna W | ✅ verificado en telecom |
| 9 | ITBIS → columna N | ✅ verificado en telecom |
| 10 | 606/202606 sin errores CDT | ✅ 0 errores, 90 válidos |

**Persistencia automática:** upgrade a `19.0.1.16.1` sin `sync` manual en shell → catálogo 154 filas con tax 5=N, 14=W, 15=X.

---

## 7. FASE 5 — 606/202606 Antes vs Después

### Comparación de errores

| Métrica | Antes (post-FDP) | Después (clasificador) | Δ |
|---|---|---|---|
| Total errores | **5** | **0** | **−5** |
| Válidos exportables | 85 | **90** | **+5** |
| Errores NCF | 0 | 0 | — |
| Errores impuesto | 5 (CDT) | **0** | **−5** |

### Errores eliminados (5 facturas telecom)

| Factura | NCF | Error antes |
|---|---|---|
| FP/2026/06/0083 | E310000000209 | impuesto no clasificado: 2% CDT |
| FP/2026/06/0084 | E310000019120 | impuesto no clasificado: 2% CDT |
| FP/2026/06/0044 | E310015894257 | impuesto no clasificado: 2% CDT |
| FP/2026/06/0045 | E310015890327 | impuesto no clasificado: 2% CDT |
| FP/2026/06/0046 | E310015893083 | impuesto no clasificado: 2% CDT |

**E310000019120:** error NCF ya resuelto por FDP; error CDT resuelto por clasificador.

### Columnas DGII pobladas (período 202606, 90 válidos)

| Columna | Total período | Descripción |
|---|---|---|
| **N** (ITBIS) | 188,376.94 | ITBIS 18%/16%/9% vía rol `itbis` |
| **W** (ISC) | 1,012.23 | ISC 10% telecom vía rol `isc` |
| **X** (Otros) | **202.45** | **CDT 2% vía rol `other_tax`** |
| **Y** (Propina) | 0.00 | Sin propinas en período |

### Muestra facturas CDT (columna X)

| Factura | NCF | N | W | **X (CDT)** |
|---|---|---|---|---|
| FP/2026/06/0083 | E310000000209 | 1,305.76 | 725.42 | **145.08** |
| FP/2026/06/0084 | E310000019120 | 0.38 | 0.21 | **0.04** |
| FP/2026/06/0044 | E310015894257 | 187.62 | 104.23 | **20.85** |
| FP/2026/06/0045 | E310015890327 | 78.44 | 43.58 | **8.72** |
| FP/2026/06/0046 | E310015893083 | 249.82 | 138.79 | **27.76** |

---

## 8. Impacto en el sistema

| Área | Impacto |
|---|---|
| Datos históricos | **Sin cambios** — solo lectura + catálogo nuevo |
| Facturas / impuestos | **Sin cambios** |
| Exportadores 606/607 | Refactor a clasificador; comportamiento corregido para CDT/ISC/otros |
| Operación futura | Nuevo impuesto → 1 fila en catálogo UI, sin deploy de código |
| Performance | Lookup O(1) por tax_id; cache ORM estándar |

---

## 9. Evidencia histórico intacto

| Check | Pre | Post |
|---|---|---|
| Posted moves | 2,255 | 2,255 |
| Partial reconciles | 947 | 947 |
| Payments active | 677 | 677 |
| NCF Adel | 1,504 | 1,504 |
| GL balanceado | ✅ | ✅ |
| Motor NCF Justech | 0 | 0 |

Healthcheck post-despliegue: **18/18 PASS**

---

## 10. Rollback

1. Restaurar backup: `/opt/odoo-dev/backups/classifier-pre-20260709_233712`
2. O revertir módulo a `19.0.1.15.0` y eliminar tabla `justech_do_dgii_tax_classification`
3. El histórico contable no se ve afectado en ningún escenario (solo metadatos de catálogo)

---

## 11. Operación — Agregar un nuevo impuesto DGII

1. Crear el `account.tax` normalmente en Odoo (sin tocar exportadores)
2. Ir a **Contabilidad → Reportes DGII → Clasificación fiscal**
3. Ejecutar **Sincronizar clasificaciones desde impuestos** (o crear manualmente)
4. Ajustar `classification_role` y columna (ej. nuevo impuesto → rol `other_tax`, columna `X`)
5. Validar período en wizard 606/607

**No se requiere modificar Python del exportador.**

---

## 12. Próximos pasos recomendados

1. **Hotfix 623** — corregir `KeyError: move_id` en `dgii_623_exporter.classify_moves`
2. **Upgrade `justech_l10n_do_base`** a `19.0.1.7.0` en dev (FDP ya desplegado en código fuente)
3. Despliegue controlado a producción **solo con aprobación explícita**
4. Commit en `feature/fiscal-integration-phase-a` cuando el usuario lo solicite

---

## 13. Archivos de evidencia

| Archivo | Contenido |
|---|---|
| `TAX_MATRIX_20260709.json` | Matriz FASE 1 (154 impuestos) |
| `post_606_202606_final.json` | 606/202606 post-clasificador (0 errores) |
| `post_606_columns_sample.json` | Columnas N/W/X/Y con CDT |
| `post_all_reports_validate.json` | Validación 606–609 |
| `CLOSURE_VALIDATE.json` | 28 checks cierre limpio |
| `FINAL_TAX_MATRIX.json` | Matriz final 154 impuestos + clasificación |
| `post_catalog_persist.json` | Persistencia post-upgrade sin sync manual |
| `../FDP-deploy-20260709/post_606_202606.json` | Baseline antes (5 errores CDT) |

---

**Resultado final:** Cierre limpio **APROBADO**. Motor parametrizable operativo. Commit `19.0.1.16.1` en `feature/fiscal-integration-phase-a`.
