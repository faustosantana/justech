# Fase 14.1 — Corrección de permisos y menús de Contabilidad

**Fecha:** 2026-06-30  
**Ambientes:** `hellenia_test` → `hellenia_prod`  
**Usuario afectado:** `it@justech.do`  
**Rama:** `cursor/phase14-1-accounting-permissions-dd85`

---

## 1. Resumen ejecutivo

| Campo | Valor |
|-------|-------|
| **Causa exacta** | Árbol de menús contables roto en PROD: submenús desconectados del raíz `account.menu_finance` bajo un contenedor huérfano *Accounting* inactivo. No era un problema de grupos — `it@justech.do` ya tenía *Accounting / Administrator*. |
| **Corrección aplicada** | `repair_accounting_menu_tree()` en `hellenia_ui`, ejecutado en upgrade del módulo + script `phase14-1-fix-accounting-permissions.py`. Alineación de grupos de `it@justech.do`. |
| **TEST** | **PASS** |
| **PROD** | **PASS** |
| **Backup PROD** | `/opt/odoo-projects/hellenia/backups/hellenia-prod/2026-06-30_1743` |

---

## 2. Síntoma reportado

En producción (`https://odoo.hellenia.cloud`), el administrador técnico `it@justech.do` veía el ícono **Contabilidad** en el menú principal, pero al entrar el módulo aparecía vacío o incompleto. En algunos casos coexistían entradas duplicadas *Facturación* + *Contabilidad*.

---

## 3. Causa raíz

### 3.1 Diagnóstico en PROD (pre-fix)

| Elemento | Estado antes del fix |
|----------|---------------------|
| `account.menu_finance` (Contabilidad, id=142) | Raíz activa, **0 hijos directos en BD** |
| Contenedor huérfano *Accounting* (id=355) | `parent_id=None`, `active=False`, contenía los submenús contables |
| Grupos de `it@justech.do` | Ya incluía `account.group_account_manager` (*Accounting / Administrator*) |
| Módulos requeridos | Todos instalados (`account`, `account_accountant`, `account_reports`, etc.) |

**Conclusión:** El usuario tenía permisos correctos, pero la estructura del menú estaba corrupta tras el renombrado de *Facturación* → *Contabilidad* por `hellenia_ui`. Los submenús (Dashboard, Clientes, Proveedores, Asientos, Informes, Configuración) quedaron bajo un nodo intermedio inactivo en lugar del raíz oficial.

### 3.2 Comparación TEST vs PROD

| Ambiente | Hijos bajo Contabilidad | Estructura |
|----------|-------------------------|------------|
| TEST | 7–11 submenús | Correcta (hijos bajo `account.menu_finance`) |
| PROD (pre-fix) | 0 en raíz, 9+ en huérfano | Rota |

---

## 4. Corrección aplicada

### 4.1 Código (`custom/hellenia_ui`)

**`models/menu_customizer.py`**

- `repair_accounting_menu_tree()` — Reparenta submenús contables bajo `account.menu_finance`, desactiva contenedores huérfanos (*Accounting*, *Facturación*, *Invoicing*).
- `hide_unused_menus()` — Xmlids alternativos para ocultar POS.
- `apply_menu_labels()` — Un solo nombre raíz: **Contabilidad**.

**`data/menu_labels.xml`** — Invoca las tres funciones en cada upgrade de `hellenia_ui`.

### 4.2 Script de validación

`scripts/phase14-1-fix-accounting-permissions.py`:

1. Audita usuarios `it@justech.do`, `admin`, `usuario.normal.demo14`.
2. Aplica customizer + grupos objetivo para `it@justech.do`.
3. Valida visibilidad real con `_visible_menu_ids()` (no búsqueda cruda de menús).
4. Genera evidencia JSON PASS/FAIL.

### 4.3 Grupos asignados a `it@justech.do`

| XML ID | Nombre visible (PROD) |
|--------|----------------------|
| `base.group_system` | Access Rights |
| `base.group_erp_manager` | Role / Administrator |
| `account.group_account_manager` | Accounting / Administrator |
| `sales_team.group_sale_manager` | Sales / Administrator |
| `purchase.group_purchase_manager` | Purchase / Administrator |
| `stock.group_stock_manager` | Inventory / Administrator |
| `base.group_no_one` | Technical Features |
| `justech_l10n_do_base.group_justech_do_fiscal_manager` | Accounting / Dominican Fiscal Manager |

---

## 5. Validación TEST

**Comando:** `bash scripts/run-phase14-1-fix.sh test`  
**Evidencia:** `evidence/phase14-1-accounting-permissions-test.json`  
**Resultado:** `ok: true`

| Criterio | Resultado |
|----------|-----------|
| `it@justech.do` ve Contabilidad con ≥5 submenús | PASS |
| `admin` ve Contabilidad con ≥5 submenús | PASS |
| `usuario.normal.demo14` NO ve Contabilidad | PASS |
| Sin raíz duplicada Facturación/Accounting | PASS |
| POS oculto | PASS |
| Módulos requeridos instalados | PASS |

### Menús visibles `it@justech.do` (TEST)

```
Discuss, Contactos, Ventas, Dashboards, Contabilidad, Compras, Inventario, Apps, Configuración
```

### Submenús Contabilidad `it@justech.do` (TEST)

```
Settings, Dashboard, Journal Entries, Customers, Vendors, Accounting, Journal Items, Review, Accounting, Reporting, Configuration
```

---

## 6. Promoción PROD

**Flujo:** TEST PASS → backup → `APPROVE_PROMOTION=1 bash scripts/promote-phase14-1-to-prod.sh`

| Paso | Estado |
|------|--------|
| Backup PostgreSQL + filestore | OK (`2026-06-30_1743`) |
| Upgrade `hellenia_ui` + script fix | OK |
| Healthcheck completo | PASS (HTTP 200, TLS, websocket, módulos fiscales) |
| Evidencia | `evidence/phase14-1-accounting-permissions-prod.json` |

**Resultado PROD:** `ok: true`

---

## 7. Estado final PROD

### Grupos finales `it@justech.do`

- Access Rights
- Accounting / Administrator
- Accounting / Dominican Fiscal Manager
- Inventory / Administrator
- Purchase / Administrator
- Role / Administrator
- Sales / Administrator
- Technical Features

### Menús raíz visibles `it@justech.do`

```
Contactos, Ventas, Contabilidad, Compras, Inventario, Apps, Configuración
```

### Submenús Contabilidad `it@justech.do`

```
Settings, Dashboard, Journal Entries, Customers, Vendors, Accounting, Journal Items, Accounting, Reporting
```

### Usuario normal (`usuario.normal.demo14`)

| Campo | Valor |
|-------|-------|
| Grupos | Sales / User: Own Documents Only |
| Menús raíz | Contactos, Ventas |
| Ve Contabilidad | **No** (`sees_contabilidad: false`) |

---

## 8. Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `custom/hellenia_ui/models/menu_customizer.py` | `repair_accounting_menu_tree()`, POS xmlids |
| `custom/hellenia_ui/data/menu_labels.xml` | Hook de reparación en upgrade |
| `scripts/phase14-1-fix-accounting-permissions.py` | Auditoría, fix, validación |
| `scripts/run-phase14-1-fix.sh` | Runner TEST/PROD |
| `scripts/promote-phase14-1-to-prod.sh` | Promoción con backup |

---

## 9. Resultado final

| Métrica | Valor |
|---------|-------|
| **TEST** | **PASS** |
| **PROD** | **PASS** |
| **Causa** | Árbol de menús contables desconectado en BD (no permisos) |
| **Fix** | Reparentado automático vía `hellenia_ui` + validación script 14.1 |
| **it@justech.do ve Contabilidad** | Sí, con 9 submenús en PROD |
