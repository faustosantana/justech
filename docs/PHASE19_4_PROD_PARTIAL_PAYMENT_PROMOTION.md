# Fase 19.4 — Promoción PROD abonos parciales

**Fecha:** 2026-07-01  
**Resultado:** **PROD PASS** (31/31)  
**Entorno:** `hellenia_prod` @ https://odoo.hellenia.cloud  
**Rama promovida:** `cursor/phase19-3-partial-payment-fix-dd85`  
**Módulo desplegado:** `hellenia_account` **19.0.1.0.23**

---

## Resumen ejecutivo

Se promovió a producción el fix certificado en TEST para **abonos parciales** en el wizard de pagos Hellenia. La validación automatizada en PROD confirma los 4 casos de negocio y reportes DGII 607/623.

| Ítem | Valor |
|------|-------|
| **PROD** | PASS |
| **Backup usado** | `/opt/odoo-projects/hellenia/backups/hellenia-prod/2026-07-01_1131` |
| **Commit promovido (HEAD)** | `963ff35` |
| **Commits base certificados TEST** | `322238e`, `bd91174` |
| **Versión TEST certificada** | 19.0.1.0.21 |
| **Versión PROD final** | 19.0.1.0.23 |
| **Evidencia** | `evidence/phase19-4-prod-partial-payment-validation.json` |
| **Rollback** | `bash /opt/odoo-projects/hellenia/scripts/restore-hellenia-prod.sh /opt/odoo-projects/hellenia/backups/hellenia-prod/2026-07-01_1131` |

---

## Pasos ejecutados

1. **Backup PROD** — `scripts/backup-hellenia-prod.sh` → `2026-07-01_1131`
2. **Verificación backup** — PG dump, filestore, custom, docker-compose, `.env`, `MANIFEST.txt` OK
3. **Promoción rama** — checkout `cursor/phase19-3-partial-payment-fix-dd85`, rsync `custom/` + `scripts/`
4. **Upgrade módulo** — `-u hellenia_account` → 19.0.1.0.23
5. **Reinicio Odoo PROD** — `docker compose up -d --force-recreate odoo`
6. **Validación** — `scripts/phase19-4-prod-partial-payment-validation.py`
7. **Logs** — sin `RPC_ERROR`, sin `OwlError`, sin traceback en ventana post-deploy

---

## Fixes adicionales requeridos en PROD (Enterprise)

El fix TEST (`19.0.1.0.21`) no bastó en PROD por diferencias **Odoo Enterprise**:

| Versión | Cambio | Motivo |
|---------|--------|--------|
| **19.0.1.0.22** | `force_payment_move=True` en abonos parciales | Sin `move_id` no había conciliación; residual quedaba en RD$11,800 |
| **19.0.1.0.23** | `force_payment_move` **solo parcial** + `payment_account_id` en setup bancario | Pago completo con `force_payment_move` dejaba factura `in_payment` (residual 0) en lugar de `paid` |

**Causa Enterprise:** `accountant` redefine `_get_invoice_in_payment_state()` → `'in_payment'`. Con cuenta outstanding (11010203) en lugar de cuenta banco del diario (11010205), `is_matched=False` y la factura no transita a `paid` aunque residual = 0.

---

## Validación PROD — 4 casos

### Caso 1 — Parcial RD$5,000 sin retención

| Campo | Esperado | Obtenido |
|-------|----------|----------|
| `payment.amount` | RD$5,000 | RD$5,000 |
| Factura | `partial` | `partial` |
| Residual | RD$6,800 | RD$6,800 |
| Detalle aplicado | RD$5,000 (no RD$11,800) | RD$5,000 |

**Pago:** `PBNKD/2026/00002`

### Caso 2 — Parcial RD$5,000 + Retención 5% Gobierno

| Campo | Esperado | Obtenido |
|-------|----------|----------|
| Retención proporcional | RD$211.86 | RD$211.86 |
| Banco neto | RD$4,788.14 | RD$4,788.14 |
| Factura | `partial` | `partial` |
| Residual | RD$6,800 | RD$6,800 |
| 607 | actualizado | PASS (moves=5) |
| 623 | actualizado | PASS (moves=0) |

**Pago:** `PBNKD/2026/00004`

### Caso 3 — Parcial RD$5,000 + ITBIS 100%

| Campo | Esperado | Obtenido |
|-------|----------|----------|
| Retención proporcional | RD$762.71 | RD$762.71 |
| Banco neto | RD$4,237.29 | RD$4,237.29 |
| Factura | `partial` | `partial` |
| Residual | RD$6,800 | RD$6,800 |

**Pago:** `PBNKD/2026/00005`

### Caso 4 — Pago completo RD$11,800

| Campo | Esperado | Obtenido |
|-------|----------|----------|
| Factura | `paid` | `paid` |
| Residual | RD$0.00 | RD$0.00 |

---

## Evidencia consolidada

```json
{
  "partial_payment": { "amount": 5000.0, "invoice_state": "partial", "residual": 6800.0 },
  "residual": 6800.0,
  "proportional_withholding_gov": 211.86,
  "proportional_withholding_itbis": 762.71,
  "607_moves": 5,
  "623_moves": 0,
  "full_payment": { "amount": 11800.0, "invoice_state": "paid", "residual": 0.0 }
}
```

---

## Errores encontrados

| Fase | Error | Resolución |
|------|-------|------------|
| Primera validación (v21) | Residual RD$11,800, sin conciliación | `force_payment_move` v22 |
| Segunda validación (v22) | Pago completo `in_payment` residual 0 | `force_payment_move` condicional + `payment_account` v23 |
| Logs post-deploy | Ninguno | — |

---

## Rollback disponible

```bash
bash /opt/odoo-projects/hellenia/scripts/restore-hellenia-prod.sh \
  /opt/odoo-projects/hellenia/backups/hellenia-prod/2026-07-01_1131
```

Backup alternativo previo (primera promoción 19.4): `2026-07-01_1126`

---

## Restricciones respetadas

- NO se modificó `odoo-pecv`
- NO se promovieron otros cambios fuera de la rama indicada
- NO se aplicaron cambios manuales improvisados en PROD (solo upgrade módulo + setup bancario vía código)

---

## Referencias

- TEST certificación: `docs/PHASE19_3_PARTIAL_PAYMENT_FIX.md`, `evidence/phase19-3-partial-payment-fix-test.json`
- Script validación PROD: `scripts/phase19-4-prod-partial-payment-validation.py`
