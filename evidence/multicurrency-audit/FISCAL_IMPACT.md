# MC-1 — Impacto fiscal RD (multimoneda)

## Principio general

La fiscalidad dominicana (NCF, DGII) opera en contexto **económico local (DOP)**. Vender en USD es válido comercialmente; los reportes DGII mayoritariamente reflejan **montos convertidos a pesos** al tipo de cambio de la operación contable.

**Custom Justech no bloquea USD** en ningún gate fiscal.

---

## NCF (justech_l10n_do_ncf)

| Aspecto | Impacto USD |
|---------|-------------|
| Asignación NCF | ✅ Sin validación moneda |
| Rangos B01–B17 | ✅ Independientes moneda |
| Void / 608 | ✅ Sin efecto moneda |
| Secuencia NCF | Numérica fiscal — no incluye USD |

**Riesgo:** Ninguno técnico. Operativo: monto impreso en comprobante = moneda factura (USD OK).

---

## DGII 606 (compras)

| Campo exportado | Fuente | Moneda efectiva |
|-----------------|--------|-----------------|
| Montos bienes/servicios | `price_subtotal` / signed | DOP equivalente vía contabilidad |
| ITBIS | Líneas impuesto | DOP |
| Retenciones | Withholding breakdown | DOP |
| Tipo gasto | NCF prefix / B13 | N/A moneda |

**No exporta:** código moneda, tasa cambio.

**Riesgo fiscal:** Bajo si contador confirma que DGII espera pesos (práctica habitual). Medio si compra USD requiere soporte documental USD aparte.

---

## DGII 607 (ventas)

| Campo | Fuente |
|-------|--------|
| Monto facturado | `amount_untaxed_signed` |
| Total con ITBIS | `amount_total_signed` |
| ITBIS | `_move_itbis_amount()` |
| Medios de pago | Inferidos de pagos conciliados |

```python
# dgii_607_exporter.py
total_untaxed = self._format_amount(move.amount_untaxed_signed)
total_with_tax = self._format_amount(move.amount_total_signed)
```

**Efecto USD:** Factura USD $1,000 a tasa 58 → 607 reporta ~RD$58,000, no $1,000.

**Riesgo:** Contador debe conciliar 607 con libros DOP, no con invoice PDF USD. Sin columna USD en archivo Excel DGII.

---

## DGII 608 (anulaciones)

Sin impacto moneda — basado en NCF voided.

---

## DGII 609 (pagos exterior)

**Único reporte con FX explícito:**

| Col | Contenido |
|-----|-----------|
| H | Código moneda (`USD`, etc.) |
| I | Tasa cambio |

Validación estricta:
- Partner extranjero + moneda ≠ DOP → requiere tasa > 0
- Campo override: `justech_do_foreign_exchange_rate`

**Riesgo:** Alto si compras USD exterior sin capturar tasa → export 609 FAIL.

---

## DGII 623

Retenciones — montos desde movimientos contables en DOP. Sin columna moneda extranjera.

---

## ITBIS en USD

- ITBIS se calcula sobre base imponible en moneda factura.
- Asiento: impuesto en DOP convertido.
- DGII 607 ITBIS debe cuadrar con líneas impuesto en DOP.

**Sin doble conversión** en código custom detectada.

---

## Matriz riesgo fiscal

| Área | Riesgo | Mitigación propuesta |
|------|--------|---------------------|
| NCF en USD | 🟢 Bajo | Ninguna |
| 607 montos | 🟡 Medio | Capacitar contador; doc interno equivalencia |
| 606 compras USD | 🟡 Medio | Validar con contador |
| 609 sin tasa | 🔴 Alto | UI campo tasa + checklist |
| Retenciones USD | 🟡 Medio | UAT withholding + FX |
| Auditor DGII vs PDF USD | 🟡 Medio | PDF equivalente DOP opcional |

---

## Conclusión fiscal MC-1

**Vender en USD NO invalida NCF ni export DGII** con el código actual. Los reportes 606/607/623 operan en **DOP equivalente**. El único punto crítico FX-fiscal es **609**. No se detectaron efectos negativos que impidan operación USD si se documenta equivalencia contable.

---

## Referencias

- `custom/justech_l10n_do_reports/models/dgii_607_exporter.py`
- `custom/justech_l10n_do_reports/models/dgii_606_exporter.py`
- `custom/justech_l10n_do_reports/models/dgii_609_exporter.py`
- `custom/justech_l10n_do_ncf/models/account_move.py`
