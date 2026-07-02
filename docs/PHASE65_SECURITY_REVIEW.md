# Fase 6.5 — Revisión de Seguridad

**Alcance:** ACL, record rules, grupos, vistas, multi-empresa  
**Fecha:** 2026-06-30

---

## 1. Resumen

Los **ACL (ir.model.access)** están definidos con separación user/manager. **No hay record rules (`ir.rule`)** — hallazgo crítico para multi-empresa. No se usa `sudo()`. Acciones sensibles parcialmente protegidas solo en UI.

**Calificación seguridad:** **B+**

---

## 2. Grupos de seguridad

| Grupo | XML ID | Implied | Evaluación |
|-------|--------|---------|------------|
| Dominican Fiscal User | `group_justech_do_fiscal_user` | `account.group_account_invoice` | ✅ |
| Dominican Fiscal Manager | `group_justech_do_fiscal_manager` | fiscal user | ✅ |

Odoo 19: usa `privilege_id` correctamente (no `category_id` deprecado).

---

## 3. ACL (ir.model.access.csv)

### base

| Modelo | User | Manager |
|--------|------|---------|
| fiscal.document.type | R | CRUD |

### ncf

| Modelo | User | Manager |
|--------|------|---------|
| ncf.range | R | CRUD |
| ncf.consumption | R | CRU (no unlink) |

✅ Consumption sin unlink para manager — **buena práctica de auditoría**.

### reports

| Modelo | User | Manager |
|--------|------|---------|
| fiscal.report | RWC | CRUD |
| fiscal.report.line | R | CRUD |
| wizard | RWCU | RWCU |

---

## 4. Record Rules — **AUSENTES**

**Ningún módulo define `ir.rule`.**

### Riesgo multi-empresa

Usuario de Compañía A con acceso a modelo `justech.do.ncf.range` podría:
- Leer rangos de Compañía B si conoce IDs
- En reportes, `company_id` es campo del formulario sin restricción server-side en wizard

### Modelos que requieren rule `[(company_id, in, company_ids)]`

- `justech.do.fiscal.document.type`
- `justech.do.ncf.range`
- `justech.do.ncf.consumption`
- `justech.do.fiscal.report`
- `justech.do.fiscal.report.line`

**Severidad: ALTA** — bloqueante para producto multi-empresa.

---

## 5. Acciones y menús

| Elemento | Protección | Gap |
|----------|------------|-----|
| Menú Dominican Fiscal | `groups=fiscal_user` | ✅ |
| Botón Void NCF | `groups=fiscal_manager` en vista | ❌ **No en Python** |
| Campos NCF en factura | `readonly` si posted | ⚠️ Editable en draft por cualquier invoice user |

### `action_void_ncf` — bypass RPC

Un usuario técnico puede llamar `action_void_ncf` vía RPC sin ser manager:

```python
def action_void_ncf(self):
    for move in self:
        if move.state != "posted":  # solo valida estado
```

**Fix:** `@api.model` check o `self.env.user.has_group(...)`.

---

## 6. `sudo()`

**0 ocurrencias** en módulos MVP — ✅ excelente.

---

## 7. Campos protegidos

| Campo | Protección vista | Protección servidor |
|-------|------------------|---------------------|
| `justech_do_ncf` | readonly si posted | constraint unique posted |
| `justech_do_ncf_voided` | readonly | write sin grupo check |
| `sequence_end` en rango | — | manager ACL only |

---

## 8. Exportación de archivos

`action_export_csv/xlsx` genera URL `/web/content/?model=...&id=...`

Odoo estándar valida ACL del modelo — ✅ usuario debe tener read en `justech.do.fiscal.report`.

---

## 9. Aislamiento entre compañías — matriz

| Vector | Aislado | Notas |
|--------|---------|-------|
| ACL por grupo | ✅ | — |
| Record rules | ❌ | **Falta** |
| `company_id` default | ⚠️ | `env.company` — OK en UI |
| Wizard company picker | ⚠️ | Sin check `company_ids` del usuario |
| NCF duplicate check | ✅ | Filtra por `company_id` |
| Range search | ✅ | Filtra por `company_id` |

---

## 10. Recomendaciones

### P0 — Bloqueantes

1. Crear `security/justech_l10n_do_rules.xml` con rules multi-empresa
2. Añadir check de grupo en `action_void_ncf`
3. Restringir `company_id` en wizard a `self.env.companies`

### P1

4. Grupo separado para export DGII (segregación de funciones)
5. Log de auditoría en void NCF (quién, cuándo, motivo obligatorio)

### P2

6. Rate limit en generación masiva de reportes (DoS interno)

---

## 11. Conclusión

Seguridad **aceptable para single-company DEV**. **No certificable** para producción multi-empresa sin record rules y hardening de acciones.

**Calificación:** **B+**
