# Fase 19.7 — Promoción PROD selección facturas wizard

**Fecha:** 2026-07-01  
**Resultado:** **PROD PASS** (14/14)  
**Entorno:** `hellenia_prod` @ https://odoo.hellenia.cloud  
**Rama promovida:** `cursor/phase19-6-selected-invoices-fix-dd85`  
**Módulo:** `hellenia_account` **19.0.1.0.24**  
**Commit promovido:** `45146e6`

---

## Resumen ejecutivo

| Ítem | Valor |
|------|-------|
| **PROD** | PASS |
| **Backup usado** | `/opt/odoo-projects/hellenia/backups/hellenia-prod/2026-07-01_1156` |
| **Commit promovido** | `45146e6` |
| **TEST previo** | PASS 24/24 (Fase 19.6) |
| **Evidencia** | `evidence/phase19-7-selected-invoices-prod.json` |
| **Rollback** | `bash /opt/odoo-projects/hellenia/scripts/restore-hellenia-prod.sh /opt/odoo-projects/hellenia/backups/hellenia-prod/2026-07-01_1156` |

---

## Pasos ejecutados

1. Backup PROD → `2026-07-01_1156` (PG dump, filestore, custom, docker-compose, `.env`, `MANIFEST.txt` verificados)
2. Promoción rama `cursor/phase19-6-selected-invoices-fix-dd85`, rsync `custom/` + script validación
3. Upgrade `-u hellenia_account` → 19.0.1.0.24
4. Reinicio Odoo PROD (`force-recreate odoo`)
5. Validación automatizada `phase19-7-selected-invoices-prod-validation.py`
6. Logs: sin `RPC_ERROR`, sin `OwlError`, sin traceback

---

## Fix promovido

- Facturas **no** vienen marcadas por defecto (`apply=False`)
- Checkbox **Aplicar** persiste (`force_save="1"`)
- Solo se procesan líneas `apply=True` (`_selected_lines()`)
- `amount_to_pay` no se reemplaza silenciosamente por residual completo

---

## Validación PROD — Escenario crítico

**Cliente con 3 facturas RD$11,800 (A, B, C). Solo A seleccionada, monto RD$5,000.**

| Campo | Esperado | Obtenido |
|-------|----------|----------|
| Pagos creados | 1 | 1 (`PBNKD/2026/00005`) |
| `payment.amount` | RD$5,000 | RD$5,000 |
| Factura A | `partial` | `partial` |
| Residual A | RD$6,800 | RD$6,800 |
| Factura B | `not_paid` | `not_paid` |
| Factura C | `not_paid` | `not_paid` |

---

## Validación PROD — Retención 5% Gobierno

**Solo factura A, RD$5,000 parcial + Retención Gobierno.**

| Campo | Esperado | Obtenido |
|-------|----------|----------|
| Pagos creados | 1 | 1 (`PBNKD/2026/00006`) |
| Retención proporcional | RD$211.86 | RD$211.86 |
| Factura A | `partial` | `partial` |
| B, C | `not_paid` | `not_paid` |
| 623 | actualizado | PASS (`moves=0` en período actual) |

---

## Errores encontrados

Ninguno en promoción ni validación post-deploy.

---

## Restricciones respetadas

- NO `odoo-pecv`
- Solo módulo `hellenia_account` actualizado
- Sin cambios manuales improvisados en PROD

---

## Referencias

- Fix TEST: `docs/PHASE19_6_SELECTED_INVOICES_PARTIAL_PAYMENT_FIX.md`
- Lógica: `docs/PAYMENT_WIZARD_SELECTION_LOGIC.md`
- Script PROD: `scripts/phase19-7-selected-invoices-prod-validation.py`
