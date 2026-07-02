# Fase 7.5 — Auditoría de Seguridad

**Cliente:** Hellenia, S.R.L.  
**Fecha:** 2026-06-30  
**Alcance:** DEV (`hellenia_dev`) y TEST (`hellenia_test`)  
**Evidencia:** `evidence/security-audit-dev.json`, `evidence/security-audit-test.json`

---

## 1. Resumen ejecutivo

| Área | DEV | TEST | Evaluación |
|------|-----|------|------------|
| Usuarios operativos | `admin` + `it@justech.do` | `admin` + `it@justech.do` | ✅ |
| Usuario técnico Justech | Creado | Creado | ✅ |
| `admin` preservado | Activo | Activo | ✅ |
| Usuarios duplicados | 0 | 0 | ✅ |
| Usuarios prueba accidentales | 0 | 0 | ✅ |
| Record rules Justech | 6 | 6 | ✅ |
| ACL Justech | 10 entradas | 10 entradas | ✅ |
| Multi-company rules (total sistema) | 54 | 54 | ✅ |
| SMTP saliente | No configurado | No configurado | ⚠️ |
| BD neutralizada | No | Sí | ✅ (TEST) |

**Calificación seguridad administrativa:** **B+** (pendiente SMTP y endurecimiento `admin`)

---

## 2. Usuarios

### 2.1 Usuarios internos activos

| Login | Nombre | Ambiente | Rol | Grupos |
|-------|--------|----------|-----|--------|
| `admin` | Administrator | DEV, TEST | Recuperación emergencia | 7 grupos admin módulo |
| `it@justech.do` | Justech IT | DEV, TEST | Administrador TI | 8 grupos (ver §2.2) |

### 2.2 Grupos asignados a `it@justech.do`

| Grupo efectivo | XML ID origen |
|----------------|---------------|
| Access Rights (Settings) | `base.group_system` |
| Role / Administrator | `base.group_erp_manager` |
| Accounting / Administrator | `account.group_account_manager` |
| Sales / Administrator | `sales_team.group_sale_manager` |
| Purchase / Administrator | `purchase.group_purchase_manager` |
| Inventory / Administrator | `stock.group_stock_manager` |
| Technical Features | `base.group_no_one` |
| Dominican Fiscal Manager | `justech_l10n_do_base.group_justech_do_fiscal_manager` |

**Idioma:** `es_DO` | **Timezone:** `America/Santo_Domingo`

La contraseña fue configurada según especificación Fase 7.5 (no documentada en repositorio).

### 2.3 Usuarios inactivos / plantillas

| Login | Tipo |
|-------|------|
| `__system__` | OdooBot (sistema) |
| `public` | Plantilla público |
| `portaltemplate` | Plantilla portal |

---

## 3. Taxonomía de grupos

| Categoría | Cantidad DEV | Descripción |
|-----------|--------------|-------------|
| Total grupos en instancia | 60 | Todos los `res.groups` |
| Estándar Odoo | 16 | Accounting, Sales, Purchase, Inventory, etc. |
| Enterprise | 1+ | `web_enterprise` y grupos EE heredados |
| Justech custom | 2 | Fiscal User, Fiscal Manager |

### 3.1 Grupos Justech

| XML ID | Nombre | Usuarios |
|--------|--------|----------|
| `justech_l10n_do_base.group_justech_do_fiscal_user` | Dominican Fiscal User | 0 |
| `justech_l10n_do_base.group_justech_do_fiscal_manager` | Dominican Fiscal Manager | 1 (`it@justech.do`) |

Implied: Fiscal Manager → Fiscal User → `account.group_account_invoice`

---

## 4. ACL (`ir.model.access`) — Módulos Justech

| Modelo | Grupo | R | W | C | D |
|--------|-------|---|---|---|---|
| `justech.do.fiscal.document.type` | Fiscal User | ✓ | | | |
| `justech.do.fiscal.document.type` | Fiscal Manager | ✓ | ✓ | ✓ | ✓ |
| `justech.do.ncf.range` | Fiscal User | ✓ | | | |
| `justech.do.ncf.range` | Fiscal Manager | ✓ | ✓ | ✓ | ✓ |
| `justech.do.ncf.consumption` | Fiscal User | ✓ | ✓ | ✓ | |
| `justech.do.ncf.consumption` | Fiscal Manager | ✓ | ✓ | ✓ | |
| `justech.do.fiscal.report` | Fiscal User | ✓ | ✓ | ✓ | |
| `justech.do.fiscal.report` | Fiscal Manager | ✓ | ✓ | ✓ | ✓ |
| `justech.do.fiscal.report.line` | Fiscal User | ✓ | | | |
| `justech.do.fiscal.report.line` | Fiscal Manager | ✓ | ✓ | ✓ | ✓ |
| `justech.do.fiscal.report.wizard` | Fiscal User / Manager | ✓ | ✓ | ✓ | |

**Nota:** Consumption sin `unlink` para manager — auditoría fiscal preservada (diseño Sprint 0).

---

## 5. Record rules (`ir.rule`)

### 5.1 Justech — multiempresa

| Modelo | Dominio |
|--------|---------|
| `justech.do.fiscal.document.type` | `company_id in company_ids` OR `company_id = False` |
| `justech.do.ncf.range` | `company_id in company_ids` |
| `justech.do.ncf.consumption` | `company_id in company_ids` |
| `justech.do.fiscal.report` | `company_id in company_ids` |
| `justech.do.fiscal.report.line` | `report_id.company_id in company_ids` |
| `justech.do.fiscal.report.wizard` | `company_id in company_ids` |

### 5.2 Sistema — multi-company

**54 record rules** estándar Odoo activas (account, stock, sale, purchase, etc.).

Compañías en instancia: **1** (`Hellenia, S.R.L.`) — reglas preparadas para expansión futura.

---

## 6. Controles revisados

| Control | Resultado |
|---------|-----------|
| Multiempresa Justech | ✅ |
| Accesos administrativos | ✅ `it@justech.do` con Settings + Technical |
| Usuarios inactivos sin uso operativo | ✅ |
| Usuarios duplicados | ✅ Ninguno |
| SMTP | ⚠️ Sin servidor saliente (DEV); TEST neutralizado mitiga envíos |
| Parámetros mail alias | ⚠️ No configurados (`catchall`, `bounce`) |
| `action_void_ncf` solo manager | ✅ Sprint 0 |
| Índice único NCF | ✅ `account_move_justech_do_ncf_company_uniq` |
| POS instalado | ✅ No — superficie reducida |

---

## 7. Cron críticos (DEV — 29 activos)

| Cron | Intervalo | Riesgo UAT |
|------|-----------|------------|
| Mail: Email Queue Manager | 1 h | ⚠️ Sin SMTP — cola no sale |
| Digest Emails | 1 día | Bajo |
| Account auto-post | 1 día | Bajo |
| Publisher warranty check | 1 semana | Bajo |
| SMS Queue | 24 h | Bajo |
| Snailmail queue | 24 h | Bajo |

En **TEST neutralizado**: crons de correo desactivados por neutralización.

---

## 8. Riesgos identificados

| ID | Riesgo | Severidad | Mitigación |
|----|--------|-----------|------------|
| R-01 | Sin SMTP en DEV | Media | Configurar antes de UAT con correo real |
| R-02 | `admin` con mismos privilegios que operación | Media | Uso solo emergencia; operar con `it@justech.do` |
| R-03 | Alias catchall/bounce sin definir | Baja | Configurar al definir dominio correo |
| R-04 | Crons activos en DEV sin neutralización | Baja | No usar correos reales en DEV |
| R-05 | `odoo.hellenia.cloud` sin router | Alta (Go-Live) | Ver GO_LIVE_READINESS.md |

---

## 9. Certificación seguridad Fase 7.5

```
Seguridad MVP Justech:     OK
Usuarios controlados:      OK
ACL + Record rules:        OK
Usuario técnico:           CREADO
admin emergencia:          PRESERVADO
SMTP:                      PENDIENTE
Riesgos bloqueantes UAT:   0 (SMTP recomendado, no bloqueante técnico)
```

**Regenerar auditoría:** `./scripts/audit-security-phase75.sh dev|test`
