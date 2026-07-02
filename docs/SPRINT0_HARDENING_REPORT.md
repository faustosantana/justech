# Sprint 0 — Hardening Report (Fase 6.5 P0)

**Cliente:** Hellenia, S.R.L.  
**Ambiente:** DEV (`hellenia_dev` / `2.25.69.179`)  
**Rama:** `feature/justech-l10n-do-mvp`  
**Versión módulos:** `19.0.1.1.0`  
**Fecha:** 2026-06-30  
**Alcance:** Corrección exclusiva de 4 ítems P0 identificados en Fase 6.5

---

## 1. Resumen ejecutivo

| Ítem | Estado |
|------|--------|
| Backup DEV pre-cambios | ✅ `backups/dev/2026-06-30_1210` verificado |
| P0 TD-001 — `ir.rule` multiempresa | ✅ Cerrado |
| P0 TD-002 — Race condition `consume_next` | ✅ Cerrado |
| P0 TD-003 — Protección `action_void_ncf` | ✅ Cerrado |
| P0 TD-004 — Constraint SQL NCF único | ✅ Cerrado |
| Tests unitarios post-hardening | ✅ **19/19** PASS |
| Validación E2E `PHASE6_MVP` | ✅ `ok: true` |
| Prueba concurrencia NCF | ✅ PASS (serialización verificada) |
| TEST / PROD / POS / core / Enterprise | ✅ No tocados |

**Veredicto:** Los 4 P0 quedaron cerrados en DEV. El MVP puede promoverse a **TEST** bajo el gate operativo habitual (backup TEST, deploy rama, re-validación).

---

## 2. Backup

| Campo | Valor |
|-------|-------|
| Ruta | `/opt/odoo-projects/hellenia/backups/dev/2026-06-30_1210` |
| PostgreSQL | `postgres_all.sql.gz` (2.2 MB) — gzip OK |
| Filestore | `filestore.tar.gz` (1.7 MB) — tar OK |
| Custom | `custom.tar.gz` — tar OK |
| Verificación | `verify-backup-dev.sh` → **backup completo y válido** |

Backup anterior Fase 6: `2026-06-30_1122` (conservado).

---

## 3. Cambios por P0

### TD-001 — Record rules multiempresa

| Módulo | Archivo | Modelos |
|--------|---------|---------|
| `justech_l10n_do_base` | `security/justech_l10n_do_rules.xml` | `justech.do.fiscal.document.type` |
| `justech_l10n_do_ncf` | `security/justech_l10n_do_ncf_rules.xml` | `justech.do.ncf.range`, `justech.do.ncf.consumption` |
| `justech_l10n_do_reports` | `security/justech_l10n_do_reports_rules.xml` | `justech.do.fiscal.report`, `.line`, wizard |

Dominio estándar: `company_id in company_ids` (tipos fiscales permiten `company_id = False`).

### TD-002 — Race condition en consumo NCF

**Archivos:** `justech_l10n_do_ncf/models/ncf_range.py`, `account_move.py`

1. `pg_advisory_xact_lock(company_id, doc_type_code)` antes de asignar NCF al publicar.
2. `_find_active_range_for_update()` — búsqueda ORM + `SELECT … FOR UPDATE` sobre candidatos.
3. `consume_next()` — lectura/actualización con `FOR UPDATE` y `UPDATE` SQL atómico de `next_sequence`.
4. Trazabilidad preservada en `justech.do.ncf.consumption`.

### TD-003 — `action_void_ncf` protegido en servidor

**Archivo:** `justech_l10n_do_ncf/models/account_move.py`

- `AccessError` si el usuario no pertenece a `group_justech_do_fiscal_manager`.
- Motivo obligatorio (`justech_do_ncf_void_reason`).
- Auditoría en consumo: `void_user_id`, `void_datetime`, `void_reason`.
- Vistas actualizadas para capturar motivo antes de anular.

### TD-004 — Índice único NCF publicado

**Archivo:** `justech_l10n_do_ncf/models/account_move.py` → `init()`

```sql
CREATE UNIQUE INDEX account_move_justech_do_ncf_company_uniq
ON account_move (company_id, justech_do_ncf)
WHERE state = 'posted'
  AND justech_do_ncf IS NOT NULL
  AND justech_do_ncf != '';
```

Complementa validación Python `_justech_check_duplicate_ncf`. Notas de crédito/débito usan prefijos distintos (B04, B03); duplicados del mismo prefijo+secuencia quedan bloqueados por compañía.

---

## 4. Pruebas

### Unitarias (`upgrade-phase6-mvp-module.sh dev`)

```
0 failed, 0 error(s) of 19 tests
```

| Módulo | Tests | Nuevos hardening |
|--------|-------|------------------|
| `justech_l10n_do_base` | 4 | `test_fiscal_document_type_record_rule` |
| `justech_l10n_do_ncf` | 13 | void manager/reason, record rules, secuencial único |
| `justech_l10n_do_reports` | 3 | `test_fiscal_report_record_rules` + reportes 607/608 |

### Concurrencia (`test-ncf-concurrency.sh dev`)

- Dos procesos `odoo shell` en paralelo publicando facturas B02 sobre rango `Sprint0 Concurrent`.
- Resultado: Worker A `B0200007001` commit exitoso; Worker B bloqueado (`SerializationFailure: concurrent update`).
- **PASS:** no hay NCF duplicado persistido.

### E2E (`validate-phase6-mvp.sh dev`)

```
PHASE6_MVP ok: true
```

Evidencia: `evidence/sprint0-phase6-validation.log`, `evidence/sprint0-concurrency.log`, `evidence/sprint0-upgrade-dev.log`

---

## 5. Scripts añadidos/actualizados

| Script | Propósito |
|--------|-----------|
| `upgrade-phase6-mvp-module.sh` | Upgrade MVP + tests en DEV |
| `validate-phase6-mvp.sh` | Wrapper E2E vía `odoo shell` |
| `test-ncf-concurrency-setup.py` | Prepara rango aislado PCC |
| `test-ncf-concurrency.py` | Worker paralelo con `commit` |
| `test-ncf-concurrency.sh` | Orquestación y veredicto PASS/FAIL |

---

## 6. Restricciones respetadas

- Sin funcionalidades nuevas fuera de P0.
- Sin instalación POS.
- Sin cambios en TEST, PRODUCCIÓN, core Odoo ni Enterprise.
- `action_post` existente validado en E2E y tests unitarios.

---

## 7. Deuda remanente (no P0)

Permanece deuda P1–P3 documentada en `docs/TECHNICAL_DEBT.md` (i18n, cobertura, formato TXT DGII, etc.). No bloquea promoción a TEST.

---

## 8. Conclusión

Sprint 0 hardening **completado en DEV**. Los 4 bloqueantes P0 de Fase 6.5 están resueltos con evidencia reproducible. Se recomienda promover a TEST siguiendo `docs/REFACTORING_PLAN.md` (gate post-P0).
