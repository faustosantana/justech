# MC-1 — Flujo PDF / documentos comerciales

## Plantillas activas

| Documento | Template | Módulo |
|-----------|----------|--------|
| Factura | `justech_invoice_template.xml` | justech_report_design |
| Cotización | `hellenia_quotation_template.xml` | justech_report_design |
| Orden compra | `justech_purchase_order_template.xml` | justech_report_design |
| Recibo pago | `report_payment_receipt.xml` | hellenia_reports |

---

## Qué muestra hoy

### Factura (`justech_invoice_template.xml`)

| Campo | Mostrado | Fuente |
|-------|----------|--------|
| Moneda | ✅ Sí | `get_jt_currency_display()` → `currency_id.name` |
| Tasa cambio | ❌ No | `invoice_currency_rate` disponible pero omitido |
| Total | ✅ Sí | Widget monetary + `display_currency: doc.currency_id` |
| Equivalente DOP | ❌ No | No calculado en template |
| ITBIS | ✅ En moneda factura | Líneas impuesto |
| NCF | ✅ | Campos Justech NCF |

### Cotización

| Campo | Mostrado |
|-------|----------|
| Moneda | ✅ `doc.currency_id` |
| Símbolo USD | ✅ PASS phase24 audit |
| Tasa | ❌ |
| Validez / vendedor | ✅ Estándar |

### Orden de compra

| Campo | Mostrado |
|-------|----------|
| Moneda | ✅ `get_jt_po_currency_display()` |
| Totales | ✅ `currency_id` |

### Recibo de pago

| Campo | Mostrado |
|-------|----------|
| Moneda pago | ✅ `o.currency_id` |
| Monto aplicado | ✅ |

---

## Helpers Python

```python
# justech_report_design/models/account_move.py
def get_jt_currency_display(self):
    return self.currency_id.name  # "USD" o "DOP"

def format_jt_monetary(self, amount):
    return formatLang(self.env, amount, currency_obj=self.currency_id)
```

Redondeo descuentos respeta `currency_id.round()`.

---

## Validación MC-1 PDF

| Requisito usuario | Estado | Gap |
|-------------------|--------|-----|
| Mostrar moneda | ✅ | — |
| Mostrar tasa | ❌ | Mejora propuesta |
| Mostrar total | ✅ | — |
| Equivalente DOP si USD | ❌ | Mejora propuesta |

**Documentado en** `docs/PHASE25_INVOICE_FISCAL_FIELD_AUDIT.md` escenario 11 USD — moneda OK, tasa no en PDF.

**Spec futura** `docs/COMMERCIAL_DOCUMENTS_SPEC.md` §2.4 — totales en moneda documento; no exige dual currency.

---

## Propuesta presentación profesional (no implementada)

Para facturas USD orientadas a cliente RD:

```
Moneda: USD
Tasa BCRD: 58.50 (fecha emisión)
Subtotal: USD 1,000.00
ITBIS 18%: USD 180.00
Total: USD 1,180.00
Equivalente referencial: RD$ 68,930.00
```

Nota legal: "Equivalente informativo; obligación fiscal en pesos según tasa DGII."

---

## wkhtmltopdf / encoding

`hellenia_reports/models/ir_actions_report.py` fuerza UTF-8 para símbolos moneda (NBSP).

---

## Riesgos PDF

| Riesgo | Impacto |
|--------|---------|
| Cliente no ve tasa usada | Medio — disputas comerciales |
| DGII auditoría usa DOP; PDF solo USD | Bajo — si contador tiene Mayor |
| Sin monto en letras | Bajo — no requerido RD |

---

## Referencias

- `custom/justech_report_design/report/invoice/justech_invoice_template.xml`
- `evidence/phase24-1g-audit/audit.json`
- `docs/COMMERCIAL_DOCUMENTS_SPEC.md`
