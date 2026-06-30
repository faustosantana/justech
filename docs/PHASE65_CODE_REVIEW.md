# Fase 6.5 — Revisión de Código

**Alcance:** ~965 LOC Python producción (excl. tests)  
**Fecha:** 2026-06-30

---

## 1. Resumen

El código sigue convenciones Odoo estándar: prefijo `justech_`, métodos privados `_justech_*`, herencia limpia, sin `sudo()`. Calidad general **buena** con gaps en i18n, concurrencia y validación defensiva.

---

## 2. Inventario por modelo

### `account.move` (ncf) — 178 líneas — **Crítico**

| Método | Tipo | Hallazgos |
|--------|------|-----------|
| `_justech_fiscal_enabled` | `@api.model` | Usa `self.env.company` — OK en UI, cuidado en cron multi-company |
| `_justech_resolve_document_type` | business | Hardcoded `env.ref`; no cubre `in_refund` |
| `_justech_should_auto_assign_ncf` | business | ✅ Clara |
| `_justech_validate_manual_ncf` | validation | `parse_ncf` puede lanzar `ValueError` si secuencia no numérica |
| `_justech_check_duplicate_ncf` | validation | Solo posted + no voided; drafts pueden duplicar NCF |
| `_justech_assign_ncf_before_post` | hook | `write()` individual por move antes de post — OK |
| `action_post` | override | ✅ Llama hook → `super()` — patrón correcto |
| `action_void_ncf` | action | ❌ Sin check de grupo en servidor; sin `void_reason` obligatorio |
| `_check_ncf_unique_constraint` | `@api.constrains` | ✅ Redundante con check manual — defensa en profundidad |

### `justech.do.ncf.range` — 150 líneas

| Método | Hallazgos |
|--------|-----------|
| `action_activate` | ✅ Valida estado y expiración |
| `consume_next` | ❌ **Sin transacción atómica** — race condition multi-usuario |
| `_find_active_range` | `search` + `filtered` Python — ineficiente con muchos rangos |
| `_validate_ncf_format` | `@api.model` en modelo incorrecto semánticamente |

### `justech.do.fiscal.report` — 300 líneas

| Método | Hallazgos |
|--------|-----------|
| `action_generate` | `unlink()` + bulk `create` — OK para MVP |
| `_lines_606/607/608` | ITBIS por nombre tax `"ITBIS"` — frágil |
| `action_export_xlsx` | Import dinámico `xlsxwriter` — fallback CSV OK |

### `res.partner` — 48 líneas

| Hallazgo | Severidad |
|----------|-----------|
| `ValidationError` sin `_()` | Media — i18n |
| `justech_do_rnc_valid` stored compute | ✅ Correcto |
| RNC 9-11 dígitos | ⚠️ No valida dígito verificador DGII |

---

## 3. Overrides y hooks

| Override | Archivo | Seguro upgrade |
|----------|---------|----------------|
| `action_post` | account_move.py | ⚠️ Vigilar si Odoo añade pre-post async |
| Ningún `create/write/unlink/copy` override | — | ✅ |

Campos fiscales usan `copy=False` — ✅ correcto al duplicar facturas.

---

## 4. Constraints

### SQL (`_sql_constraints`) — **Deprecado Odoo 19**

```
WARNING: Model attribute '_sql_constraints' is no longer supported,
please define models.Constraint on the model.
```

Afecta: `fiscal.document.type`, `ncf.range`

**Recomendación:** migrar a `models.Constraint` antes de Odoo 20.

### Python (`@api.constrains`)

| Modelo | Constraint | Evaluación |
|--------|------------|------------|
| `res.partner` | RNC formato DO | ✅ |
| `fiscal.document.type` | code/prefix/series | ✅ |
| `ncf.range` | date_from/date_to | ✅ |
| `account.move` | NCF unique posted | ✅ Falta constraint SQL único |

---

## 5. Internacionalización

| Archivo | Strings `_()` | Sin traducir |
|---------|---------------|--------------|
| account_move.py | ✅ Mayoría | — |
| ncf_range.py | ✅ | — |
| res_partner.py | ❌ | ValidationError en inglés hardcoded |
| fiscal_document_type.py | ❌ | ValidationError en inglés |

**No existe carpeta `i18n/`** en ningún módulo MVP.

---

## 6. Naming conventions

| Aspecto | Cumplimiento |
|---------|--------------|
| Modelos `justech.do.*` | ✅ |
| Campos `justech_do_*` | ✅ |
| Métodos privados `_justech_*` | ✅ |
| XML IDs `doc_type_b01` | ✅ Estables |

---

## 7. Imports y typing

- Sin type hints (aceptable en Odoo 19)
- Sin `from __future__ import annotations` en modelos (solo en script validación)
- Imports ordenados y mínimos ✅

---

## 8. Excepciones

| Uso | Evaluación |
|-----|------------|
| `UserError` — reglas negocio usuario | ✅ Correcto |
| `ValidationError` — integridad datos | ✅ Correcto |
| `assertRaises(Exception)` en tests | ⚠️ Demasiado amplio — preferir `UserError` |

---

## 9. Hallazgos por severidad

### Críticos (P0)

1. Race condition en `consume_next` — dos posts simultáneos pueden obtener mismo NCF
2. `action_void_ncf` sin autorización server-side

### Altos (P1)

3. `parse_ncf` sin try/except en validación manual
4. `_sql_constraints` deprecado
5. Duplicados NCF permitidos en borrador

### Medios (P2)

6. Mensajes sin `_()` en base
7. ITBIS detectado por string en nombre de impuesto
8. Campo `justech_do_ncf_alert_days` sin implementar

### Bajos (P3)

9. Tests con `assertRaises(Exception)` genérico
10. Falta docstrings en métodos públicos de negocio

---

## 10. Conclusión

Código **limpio y legible**, patrones Odoo respetados. Los problemas principales son **concurrencia**, **seguridad de acciones** y **deuda Odoo 19→20**, no estilo o estructura interna.

**Calificación código:** **A-**
