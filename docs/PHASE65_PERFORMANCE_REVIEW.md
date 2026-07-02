# Fase 6.5 — Revisión de Performance

**Alcance:** MVP Justech l10n DO  
**Fecha:** 2026-06-30

---

## 1. Resumen

El MVP opera sobre volúmenes pequeños (Hellenia DEV) sin problemas. Para producción con miles de facturas/mes, hay **cuellos de botella predecibles** en reportes y asignación NCF concurrente.

**Calificación performance:** **B+**

---

## 2. Índices de base de datos

| Campo | Modelo | Index | Evaluación |
|-------|--------|-------|------------|
| `justech_do_ncf` | account.move | ✅ `index=True` | Correcto para duplicados y reportes |
| `ncf` | justech.do.ncf.consumption | ✅ `index=True` | Correcto |
| `company_id` | varios | FK implícito | ✅ |
| `state` + `document_type_id` | ncf.range | ❌ No compuesto | Recomendado para `_find_active_range` |

**Índice recomendado (futuro):**
```sql
-- Conceptual: (company_id, document_type_id, state) en justech_do_ncf_range
```

---

## 3. Consultas repetidas y N+1

### `account.move._justech_assign_ncf_before_post`

Por cada move en batch post:
- `_justech_resolve_document_type` → hasta 4× `env.ref()` (cache XML ID — bajo costo)
- `_justech_check_duplicate_ncf` → 1× `search()` 
- `_find_active_range` → 1× `search()` + filter Python
- `consume_next` → 1× `create` consumption + 1× `write` range + 1× `write` move

**Batch post de 50 facturas:** ~150+ queries. Aceptable para MVP.

### `justech.do.fiscal.report._lines_606/607`

```python
moves = self.env["account.move"].search(domain)  # 1 query
for move in moves:
    move.line_ids.filtered(...)  # N queries (prefetch ayuda si line_ids cargado)
```

| Escenario | Moves | Queries estimadas | Riesgo |
|-----------|-------|-------------------|--------|
| 100 compras/mes | 100 | ~101 | Bajo |
| 10 000 compras/año | 10 000 | ~10 001+ | **Alto** |

**Recomendación:** usar `read_group` o SQL directo / vista materializada para reportes DGII oficiales.

---

## 4. `filtered()` en Python vs dominio

### `_find_active_range`

```python
ranges = self.search(domain, order="date_to")
specific = ranges.filtered(lambda r: journal in r.journal_ids)
ranges = ranges.filtered(lambda r: r.date_to >= today and ...)
```

Con <20 rangos activos: negligible. Con cientos: mover filtros a dominio SQL.

---

## 5. `write()` múltiples

| Ubicación | Patrón | Impacto |
|-----------|--------|---------|
| `consume_next` | create + write range | 2 writes — necesario |
| `_justech_assign_ncf_before_post` | write move antes de post | 1 write/move — OK |
| `action_generate` | unlink lines + write con O2M | OK para reportes puntuales |

**No hay write() en loops masivos problemáticos** fuera de reportes.

---

## 6. Campos compute / store

| Campo | Store | Evaluación |
|-------|-------|------------|
| `justech_do_rnc_valid` | ✅ store=True | Correcto — usado en vistas |
| `remaining_count` | ❌ compute | OK — rango pequeño de registros |
| `prefix` en range | ✅ related store | Correcto para búsquedas |
| `company_id` en consumption | ✅ related store | Correcto para rules futuras |

---

## 7. `sudo()` y `read_group`

- **`sudo()`:** 0 usos — ✅ excelente
- **`read_group`:** 0 usos — oportunidad en reportes

---

## 8. Concurrencia (performance + integridad)

**Problema crítico:** `consume_next` no usa lock:

```
Usuario A: read next_sequence=1000
Usuario B: read next_sequence=1000
Usuario A: write 1001, NCF B0200001000
Usuario B: write 1001, NCF B0200001000  ← DUPLICADO
```

**Mitigación:** `FOR UPDATE` en browse del rango o campo `sequence_lock` con retry.

---

## 9. Exportación CSV/XLSX

- CSV: en memoria (`StringIO`) — OK hasta ~50k líneas
- XLSX: `xlsxwriter` in-memory — OK hasta ~100k celdas
- Sin streaming — riesgo memoria en reportes anuales grandes

---

## 10. Recomendaciones priorizadas

| ID | Acción | Impacto |
|----|--------|---------|
| PERF-01 | Lock en `consume_next` | Crítico |
| PERF-02 | Índice compuesto en `ncf.range` | Medio |
| PERF-03 | Prefetch `line_ids` en reportes: `search` con `prefetch_fields` | Medio |
| PERF-04 | `read_group` para totales ITBIS en reportes | Alto (futuro) |
| PERF-05 | Paginación en generación reportes >5000 líneas | Medio |

---

## 11. Conclusión

Performance **adecuada para MVP y UAT**. No está optimizada para **alto volumen** ni **concurrencia multi-usuario** en emisión simultánea de facturas.

**Calificación:** **B+**
