# MC-1 — Performance multimoneda

## Alcance evaluación

Impacto de listas de precios, tasas de cambio y conversión en operación típica Justech/Hellenia (<500 productos, <50 usuarios, RD retail/import).

**Método:** Análisis arquitectónico (sin load test PROD — restricción MC-1).

---

## Listas de precios

| Factor | Impacto | Notas |
|--------|---------|-------|
| Reglas por producto | Bajo | Odoo cachea pricelist por partner |
| Reglas por categoría | Bajo-Medio | Evalúa árbol categoría |
| Múltiples listas (DOP+USD) | Bajo | 2–3 listas estándar |
| Fechas vigencia | Bajo | Index en items |
| Descuentos por volumen | Medio | Más reglas = más CPU en SO line create |

**Umbral recomendado:** <5,000 reglas pricelist item sin problema. Hellenia << umbral.

**Anti-pattern:** Miles de reglas por SKU/cliente sin categorización.

---

## Tasas de cambio

| Operación | Costo |
|-----------|-------|
| `_convert()` por línea factura | Despreciable |
| Lookup tasa por fecha | 1 query; cache ORM |
| Historial largo (10+ años daily) | Bajo — tabla pequeña |
| `currency_rate_live` cron | 1 API call/día — negligible |

---

## Conversión en documentos

| Punto | Queries extra |
|-------|---------------|
| SO → INV | Tasa fecha factura |
| Payment reconcile FX | Asiento adicional 2-4 líneas |
| Withholding `_convert` | Por línea retención |
| DGII export 607 | Lee signed fields — sin reconversión |

---

## Reportes

| Reporte | Multimoneda cost |
|---------|------------------|
| Mayor | Columna amount_currency — OK |
| Balance/P&G EE | Consolidación DOP — estándar EE |
| DGII Excel export | Batch moves period — O(n) moves |
| PDF QWeb | Sin conversión runtime extra |

---

## Consultas sensibles

1. **Aging CxC multimoneda** — Odoo nativo; OK.
2. **Dashboard ventas USD** — Requiere filtros `currency_id`; no custom dashboard detectado.
3. **Audit log list_price** — Campo auditado; sin impacto runtime ventas.

---

## POS (futuro)

Multimoneda POS no implementado. Odoo POS multimoneda añade complejidad sesión — **no recomendado v1** Hellenia.

---

## Recomendaciones performance

| Prioridad | Acción |
|-----------|--------|
| Bajo | Mantener <3 listas activas |
| Bajo | Archivar tasas >3 años si no requeridas |
| Medio | Index DB estándar Odoo suficiente |
| Bajo | Evitar computed fields custom en price_unit |

---

## Veredicto

**Impacto performance multimoneda: BAJO** para escala Hellenia/Justech RD con arquitectura propuesta (DOP + 2 listas + tasas diarias).

No se requiere optimización especial pre go-live.
