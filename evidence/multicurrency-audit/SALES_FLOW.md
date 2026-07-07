# MC-1 — Flujo ventas multimoneda

## Cadena documental

```
product.template (list_price DOP)
        ↓
product.pricelist (USD o DOP)
        ↓
sale.order (currency_id = pricelist.currency)
        ↓
account.move out_invoice (hereda moneda)
        ↓
NCF + PDF + DGII 607
        ↓
account.payment + conciliación + FX
```

---

## Producto y precio

| Pregunta | Respuesta Odoo |
|----------|----------------|
| ¿Precio general del producto? | `list_price` en **DOP** |
| ¿Precio USD en ficha producto? | Regla en lista USD (pestaña Precios) |
| ¿Variantes? | Misma lógica; reglas por variante opcionales |
| ¿Atributos (+talla, color)? | No cambian moneda |

**Observación usuario confirmada:** DOP en campo venta + USD en pestaña Precios = **correcto**.

---

## Listas de precios

### Hellenia actual

| Lista | Moneda | Origen |
|-------|--------|--------|
| Default | DOP | Odoo |
| Lista pública DOP | DOP | Fase 8 script |
| Lista USD | ❌ No creada en script | Pendiente doc |

### Comportamiento estándar

1. Partner tiene `property_product_pricelist` (o usa default compañía).
2. SO hereda pricelist → `currency_id`.
3. Líneas calculan `price_unit` vía reglas:
   - Precio fijo en moneda lista
   - % descuento sobre `list_price` (convertido)
   - Formula por categoría / cantidad mínima

### Prioridades

- Reglas más específicas (producto > categoría > global).
- `min_quantity`, fechas `date_start`/`date_end`.
- Secuencia numérica en item.

---

## Simulación: producto lista USD

| Paso | Qué ocurre |
|------|------------|
| 1. Producto X, list_price RD$5,850 | Referencia interna DOP |
| 2. Regla lista USD: $100 fijo | Precio comercial export |
| 3. Cotización cliente USD | SO currency=USD, línea $100 |
| 4. Tasa hoy 58.50 | Equivalente ~RD$5,850 (referencia) |
| 5. Tasa mañana 59.00 | Nueva cotización recalcula si usa % sobre base; precio fijo $100 no cambia |
| 6. Confirmar pedido ayer, facturar hoy | Factura USD $100; tasa = fecha factura |
| 7. PDF | Muestra USD; ITBIS calculado en moneda factura |
| 8. NCF B01 | Asignado normalmente — **sin validación moneda** |
| 9. Asiento | CxC e ingresos en DOP convertido |

---

## Cotización vieja vs nueva tasa

| Estado SO | Efecto cambio tasa |
|-----------|-------------------|
| Draft/Sent | Vendedor puede actualizar precios manualmente o re-aplicar pricelist |
| Sale (confirmado) | `price_unit` congelado en líneas |
| Facturado | Move posted — inmutable |

**Riesgo comercial:** Cliente ve cotización USD fija; variación DOP equivalente solo afecta contabilidad interna si no se factura inmediatamente.

---

## Impuestos

- ITBIS 18% se calcula sobre base en **moneda del documento**.
- Factura USD: ITBIS en USD; asiento impuesto convierte a DOP.
- Retenciones Hellenia: wizard calcula en moneda factura; `_convert` a DOP para asiento retención.

---

## NCF

- `justech_l10n_do_ncf` **no valida moneda**.
- USD invoice recibe NCF igual que DOP.
- Monto NCF / DGII no almacena USD por separado en NCF string.

---

## PDF ventas

| Elemento | Cotización | Factura Justech |
|----------|------------|-----------------|
| Moneda | `doc.currency_id` | `get_jt_currency_display()` |
| Tasa | No mostrada | No mostrada |
| Equivalente DOP | No | No |
| ITBIS | Moneda doc | Moneda doc |

Evidencia: USD quotation PDF PASS (`evidence/phase24-1g-audit/`).

---

## Custom Hellenia relevante

| Módulo | Impacto ventas USD |
|--------|-------------------|
| `justech_report_design` | Formato monetary en `currency_id` |
| `hellenia_ux` | Label tasa en formulario factura |
| `justech_l10n_do_ncf` | Sin filtro moneda |
| `justech_l10n_do_reports` | 607 usa `amount_*_signed` |

---

## Gaps ventas

1. Lista USD no formalizada en golden config.
2. Sin política comercial documentada (¿cuándo usar lista USD?).
3. Sin UAT: SO USD → INV → PAY USD → PAY DOP cross-currency.
4. PDF sin tasa ni dual display DOP.
