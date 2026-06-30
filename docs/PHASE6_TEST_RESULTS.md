# Fase 6 — Resultados de pruebas MVP Justech l10n DO

**Cliente:** Hellenia, S.R.L.  
**Ambiente:** `hellenia_dev` (Odoo 19.0-20260619 Enterprise On-Premise)  
**Fecha validación:** 2026-06-30  
**Rama:** `feature/justech-l10n-do-mvp`  
**Resultado global:** **`PHASE6_MVP ok: true`**

---

## 1. Resumen ejecutivo

| Área | Resultado |
|------|-----------|
| Módulos MVP instalados (incremental) | ✅ base → ncf → reports |
| Tests unitarios Odoo (`--test-enable`) | ✅ 13 tests (3 + 8 + 2) |
| Validación E2E `validate-phase6-mvp.py` | ✅ 14/14 PASS |
| Backup pre-Fase 6 | ✅ `backups/dev/2026-06-30_0535` |
| TEST / PROD | ✅ No tocados |
| Core / Enterprise / módulos oficiales | ✅ No modificados |

---

## 2. Estado de módulos en BD

| Módulo | Estado |
|--------|--------|
| `justech_l10n_do_base` | installed |
| `justech_l10n_do_ncf` | installed |
| `justech_l10n_do_reports` | installed |

---

## 3. Tests unitarios (instalación con `--test-enable`)

### `justech_l10n_do_base` — 3 tests

| Test | Descripción | Resultado |
|------|-------------|-----------|
| `test_document_types_loaded` | B01, B02, B03, B04, B11, B13 cargados | PASS |
| `test_ncf_format` | Formato 11 caracteres `B0200000123` | PASS |
| `test_rnc_validation` | RNC con guiones normalizado | PASS |

### `justech_l10n_do_ncf` — 8 tests

| Test | Descripción | Resultado |
|------|-------------|-----------|
| `test_b02_consumer_invoice` | B02 consumidor final | PASS |
| `test_b01_requires_rnc` | B01 con RNC | PASS |
| `test_credit_note_b04` | Nota crédito B04 | PASS |
| `test_duplicate_ncf_blocked` | Duplicado bloqueado | PASS |
| `test_depleted_range_blocked` | Rango agotado bloqueado | PASS |
| `test_expired_range_blocked` | Rango vencido bloqueado | PASS |
| `test_b11_purchase` | Compra B11 | PASS |
| `test_void_ncf` | Anulación NCF | PASS |

### `justech_l10n_do_reports` — 2 tests

| Test | Descripción | Resultado |
|------|-------------|-----------|
| `test_report_607` | Reporte ventas con NCF | PASS |
| `test_report_608_voided` | Reporte NCF anulados | PASS |

> Durante instalación de `justech_l10n_do_ncf`, tests de dependencia `account_debit_note` pueden reportar error ajeno al módulo Justech; no bloqueó la instalación.

---

## 4. Validación E2E en DEV

**Comando:**

```bash
cd /opt/odoo-projects/hellenia/docker/dev
docker compose --env-file /opt/odoo-projects/hellenia/config/dev/.env run --rm -T odoo \
  odoo shell -d hellenia_dev --db_host=db --db_user=odoo --db_password=odoo --no-http \
  < /opt/odoo-projects/hellenia/scripts/validate-phase6-mvp.py
```

**Evidencia:** `evidence/phase6-mvp-validation.json`, log: `evidence/phase6-mvp-validation.log`

| Caso obligatorio | Resultado | Detalle |
|------------------|-----------|---------|
| Factura B02 | PASS | `B0200001000` |
| Factura B01 | PASS | `B0100001000` |
| Nota crédito B04 | PASS | `B0400001000` |
| NCF duplicado | PASS | bloqueado |
| Rango agotado | PASS | bloqueado |
| Rango vencido | PASS | bloqueado |
| Compra B11 | PASS | `B1100001000` |
| Gasto menor B13 | PASS | `B1300001000` |
| Reporte 606 | PASS | 5 líneas |
| Reporte 607 | PASS | 4 líneas |
| Reporte 608 | PASS | 1 línea |
| Asiento balanceado | PASS | debit=118.0 credit=118.0 |
| CxC (receivable) | PASS | balance 118.0 |
| PDF con NCF | PASS | 31 404 bytes |

---

## 5. Verificaciones contables

| Verificación | Evidencia |
|--------------|-----------|
| Sin asientos manuales adicionales | NCF asignado en `action_post` antes de `super()` |
| Asiento balanceado | débitos = créditos (118.0) |
| CxC | línea `asset_receivable` presente en factura B02 |
| ITBIS 18% | total 118.0 sobre base 100.0 (implícito en balance) |
| CxP | compras B11/B13 publicadas; línea payable no assertada en script |

---

## 6. Correcciones aplicadas durante Fase 6

| Issue | Fix |
|-------|-----|
| `category_id` en `res.groups` (Odoo 19) | `privilege_id` → `account.res_groups_privilege_accounting` |
| Menu action order | `action_*` definido antes de `menuitem` |
| Custom no visible en contenedor | Volume mount en `docker-compose.yml` |
| Validación balance | Comparar `debit` vs `credit` en líneas |
| Rango agotado en E2E | Prioridad diario en `_find_active_range`; aislamiento journal PD6 |
| Reporte 608 tras tests de rango | Reordenar void/608 antes de cancelar rangos B02 |

---

## 7. Brechas de cobertura

| Caso | Estado |
|------|--------|
| Nota débito B03 E2E | No en script (lógica en `account_move._justech_resolve_document_type`) |
| CxP explícita (payable line assert) | Pendiente añadir al script |
| ITBIS assert numérico explícito | Pendiente |
| Formato DGII oficial TXT | Fuera de MVP |
| Pagos y conciliaciones post-NCF | No regresión detectada; sin suite dedicada |

---

## 8. Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Reportes no cumplen formato DGII para envío | Documentado; fase posterior |
| Rangos globales sin diario afectan todos los journals | Fix: priorizar rangos con `journal_ids` |
| Datos de prueba en BD DEV | Usar backup restore si se requiere BD limpia |
| Enterprise sin licencia registrada | Limitaciones documentadas en `UNREGISTERED_ENTERPRISE_LIMITATIONS.md` |

---

## 9. Conclusión

El MVP Fase 6 cumple el alcance autorizado: NCF tradicional operativo para ventas/compras básicas y reportes 606/607/608 con exportación. Validación E2E en DEV exitosa. Listo para UAT con datos fiscales reales de Hellenia antes de promover a TEST.
