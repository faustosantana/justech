# Fase 18.4 — Corrección cálculo retenciones ITBIS

**Ambiente:** TEST (`hellenia_test` @ `test.hellenia.cloud`)  
**Módulo:** `hellenia_account` **19.0.1.0.9**  
**Fecha UTC:** 2026-07-01

---

## Veredicto

| Métrica | Resultado |
|---------|-----------|
| **TEST cálculo retenciones** | **PASS** |
| **Producción** | **NO promover** sin aprobación explícita |

---

## Causa exacta

`compute_withholding_amount()` aplicaba:

```text
monto = abs(tax_id.amount / 100) × base
```

Para retenciones ITBIS con `base_type = itbis`, la base era el **ITBIS facturado** (RD$1,800), pero `tax_id.amount` en `l10n_do` guarda la **tasa efectiva sobre base imponible** (p. ej. `-18` para “100% ITBIS”, que equivale al 18% del subtotal).

Resultado erróneo ITBIS 100%:

```text
1,800 × 18% = RD$324   ← incorrecto
```

El sistema interpretaba el 18% del impuesto ITBIS como porcentaje de retención sobre el ITBIS, en lugar del 100% nominal.

---

## Fórmula corregida

| Tipo | Base | Fórmula |
|------|------|---------|
| ITBIS 30/75/100% | ITBIS facturado | `ITBIS × (tasa_nominal / 100)` |
| ISR 2/5/10% | Base imponible | `base_imponible × (tasa_nominal / 100)` |

Implementación:

- Campo `withholding_rate` en especificación del catálogo (30, 75, 100, 5, 2, 10…)
- `rate` en catálogo = tasa **nominal** mostrada al usuario
- `compute_withholding_amount()` usa `rate` × base configurada

---

## Resultados validados (factura RD$10,000 + ITBIS RD$1,800)

| Retención | Esperado | Obtenido |
|-----------|----------|----------|
| ITBIS 30% | RD$540 | RD$540 |
| ITBIS 100% | RD$1,800 | RD$1,800 |
| ITBIS informal 75% | RD$1,350 | RD$1,350 |
| Gobierno 5% | RD$500 | RD$500 |
| ISR 2% | RD$200 | RD$200 |
| Honorarios 10% | RD$1,000 | RD$1,000 |
| Proveedor informal 10% | RD$1,000 | RD$1,000 |

### Combinaciones

| Escenario | Retenciones | Total retenido | Neto |
|-----------|-------------|----------------|------|
| ITBIS 30% + ISR 2% | RD$540 + RD$200 | RD$740 | RD$11,060 |
| ITBIS 100% + ISR 10% | RD$1,800 + RD$1,000 | RD$2,800 | RD$9,000 |

---

## Evidencia contable (TEST)

Pago proveedor con ITBIS 30% + ISR 2% sobre factura RD$11,800:

- Neto transferido banco: **RD$11,060**
- Suma retenciones write-off: **RD$740**
- Asiento: **balanceado**

---

## UI

Wizard de pagos muestra por factura:

- Base imponible
- ITBIS facturado
- Retención seleccionada
- Tipo de base / monto base / porcentaje / monto retenido
- Total retenido y neto a pagar/cobrar

---

## Regresión

| Script | Resultado | Notas |
|--------|-----------|-------|
| `phase18-4-withholding-calculation-test.py` | **PASS** | Validación principal |
| `phase18-2-validate-withholding-catalog-test.py` | 21/22 | Fallo 606 fechas período (preexistente) |
| `phase18-3-certify-withholding-test.py` | 22/23 | Fallo 606/607 fechas período (preexistente) |

---

## Archivos modificados

- `custom/hellenia_account/models/hellenia_withholding_catalog.py`
- `custom/hellenia_account/wizards/payment_partner_wizard.py`
- `custom/hellenia_account/views/payment_partner_wizard_views.xml`
- `scripts/phase18-4-withholding-calculation-test.py`

---

## Promoción a producción

**No autorizada.** Requiere aprobación explícita del usuario, backup PROD y `-u hellenia_account` en producción.
