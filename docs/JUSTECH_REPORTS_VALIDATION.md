# Fase 13.2 — Validación reportes Justech (606, 607, 608)

**Fecha:** 2026-06-30 (UTC)  
**Módulo:** `justech_l10n_do_reports` v19.0.1.2.0  
**Evidencia:** `evidence/phase13-2-validate-test.json`, `evidence/phase13-2-validate-prod.json`

---

## Resumen

| Reporte | TEST | PROD | Estado |
|---------|------|------|--------|
| 606 — Compras | 106 líneas | Validado | PASS |
| 607 — Ventas | 156 líneas | Validado | PASS |
| 608 — NCF anulados | 2 líneas | Validado | PASS |

---

## Mejoras implementadas (v1.2.0)

### Presentación en español

- Tipo de reporte: "606 — Compras", "607 — Ventas", "608 — NCF anulados"
- Estado: Borrador / Generado
- Botones: Regenerar, Exportar CSV, Exportar Excel
- Menús: Reportes DGII → Generar reporte / Historial de reportes

### Metadatos y trazabilidad

| Campo | Descripción |
|-------|-------------|
| `generated_at` | Fecha y hora de generación |
| `generated_by_id` | Usuario que generó |
| `company_id` | Compañía |
| `date_from` / `date_to` | Período |
| `line_count` | Cantidad de líneas |
| `total_untaxed` | Subtotal gravado |
| `total_tax` | Total ITBIS |
| `total_amount` | Total general |

### Exportación

- **CSV:** encabezados en español (RNC, Cliente/Proveedor, NCF, Monto gravado, ITBIS, Total)
- **Excel:** bloque de metadatos (compañía, período, usuario, totales) + datos tabulares

### Detección ITBIS

Anteriormente solo por nombre (`"ITBIS" in tax_line_id.name`). Ahora también por tasa fiscal estándar RD (8%, 9%, 16%, 18%).

---

## Validación con facturas reales (TEST)

Datos alimentados desde `account.move` publicados en el período:

| Reporte | Líneas | Total general |
|---------|--------|---------------|
| 606 | 106 | 93,161.00 |
| 607 | 156 | 452,037.56 |
| 608 | 2 | N/A (anulaciones) |

Incluye facturas de prueba P13.2: B01, B02, B04, B11, B13 y anulación NCF.

---

## Criterios de aceptación

| Criterio | Cumple |
|----------|--------|
| Nombre claro en español | Sí |
| Período y compañía | Sí |
| Totales y subtotales | Sí |
| Filtros por fecha | Sí |
| Estado del reporte | Sí |
| Fecha de generación | Sí |
| Usuario generador | Sí |
| Trazabilidad a `move_id` | Sí |
| Exportación CSV/Excel | Sí |
| Datos correctos | Sí (validado contra facturas) |
| Cero textos operativos en inglés (Justech) | Sí |

---

## Pendientes / deuda técnica

| ID | Descripción | Prioridad |
|----|-------------|-----------|
| TD-008 | Formato DGII oficial (columnas exactas DGII) — MVP usa columnas legibles | Media |
| TD-009 | Archivos `i18n/es.po` en módulos Justech (textos ya en español en código/XML) | Baja |

---

## Conclusión

Los reportes 606, 607 y 608 son **funcionales, presentables y operativos en español** para el MVP Justech. Validados en TEST y PROD con evidencia JSON.
