# Fase 19.9 — Fix real selección facturas (UI + servidor)

**Fecha:** 2026-07-01  
**Rama:** `cursor/phase19-9-selected-invoice-real-ui-fix-dd85`  
**Módulo:** `hellenia_account` **19.0.1.0.25**  
**Commit:** `3adc182`

---

## Resultado

| Entorno | Resultado |
|---------|-----------|
| **TEST** | **PASS** (14/14) |
| **PROD** | **PASS** (14/14) — cliente real `SMOKE P13.4 CF` |

---

## Causa raíz real

**v19.0.1.0.24 no resolvió el flujo UI** porque:

| Problema | Efecto |
|----------|--------|
| `amount_to_pay = residual` al cargar todas las líneas | B y C tenían RD$11,800 aunque `apply=False` |
| Guardado parcial del formulario editable | Solo la línea editada se envía al servidor |
| Filtro solo por `apply` en ORM | Insuficiente si montos residuales permanecían en líneas no marcadas |

El síntoma en producción: **3 pagos de RD$11,800** al abonar RD$5,000 en una sola factura.

---

## Hipótesis evaluadas

| # | Hipótesis | Resultado |
|---|-----------|-----------|
| 1 | `apply` llega True en servidor sin marcar | **Descartada** — carga con `apply=False` |
| 2 | Checkbox no persiste (UI parcial) | **Confirmada** — mitigada con guard SQL + `amount=0` |
| 3 | Editable list no envía valores | **Confirmada** — simulada con `write` parcial |
| 4 | Botón no guarda wizard | **Parcial** — Odoo guarda al click; guard servidor compensa |
| 5 | `action_register_payments` usa `line_ids` completo | **Descartada** |
| 6 | `_selected_lines` no filtra | **Descartada** — ahora usa SQL |
| 7 | `active_ids` con todas las facturas | **Descartada** — `[invoice.id]` |
| 8 | Register recibe todas | **Descartada** |
| 9 | Reload remarca todas | **Descartada** (salvo cambio partner) |
| 10 | Vista/assets viejos en cliente | **Posible** — recomendar Ctrl+F5 |
| 11 | Módulo no cargado | **Descartada** — PROD en 19.0.1.0.25 |
| 12 | Otro wizard/acción | **Descartada** — `hellenia.payment.partner.wizard` |

---

## Corrección (v25)

Ver `docs/PAYMENT_WIZARD_SERVER_SIDE_SELECTION_GUARD.md`.

Archivos:
- `payment_partner_wizard.py` — guards, SQL, logs
- `payment_partner_wizard_views.xml` — readonly condicional

---

## Evidencia UI (simulación formulario real)

No shell directo `line.write(apply=True)` únicamente — se probó:

1. **Guardado parcial** (`write` con solo línea A) — patrón del navegador
2. **`web_save()`** — ruta Odoo 19
3. **Logs PROD** con `SMOKE P13.4 CF`:

```
selected=['INV/2026/00012']
lines=[A apply=True amount=5000, B apply=False amount=0, C apply=False amount=0]
active_ids=[133]
```

### PROD — Caso crítico SMOKE P13.4 CF

| Campo | Resultado |
|-------|-----------|
| Pagos creados | 1 (`PBNKD/2026/00004`) |
| Monto | RD$5,000 |
| Factura A | `partial`, residual RD$6,800 |
| Factura B | `not_paid` |
| Factura C | `not_paid` |
| Pagos RD$11,800 | Ninguno |

---

## Promoción PROD

| Ítem | Valor |
|------|-------|
| Backup | `/opt/odoo-projects/hellenia/backups/hellenia-prod/2026-07-01_1210` |
| Rollback | `bash scripts/restore-hellenia-prod.sh <backup>` |

---

## Bug cerrado

**Sí** — con reserva: validar manualmente en UI con Ctrl+F5 si el navegador tenía assets viejos. El guard servidor v25 impide procesar facturas no marcadas aunque la UI falle al persistir.

---

## Evidencia

- `evidence/phase19-9-selected-invoice-real-ui-test.json`
- `evidence/phase19-9-selected-invoice-real-ui-prod.json`
