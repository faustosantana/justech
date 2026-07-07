# MC-1 — Flujo compras multimoneda

## Escenarios

| Proveedor | Moneda PO | Moneda factura | Uso típico RD |
|-----------|-----------|----------------|---------------|
| Local DOP | DOP | DOP | Mayoría compras |
| Importador USD | USD | USD | Inventario importado |
| Exterior servicios | USD/EUR | USD | DGII 609 |

---

## Purchase order

| Campo | Comportamiento |
|-------|----------------|
| `currency_id` | Manual o desde proveedor `property_purchase_currency_id` |
| `pricelist_id` | No aplica igual que ventas; precio en PO directo |
| Líneas `price_unit` | Moneda PO |
| Recepción | `stock` en DOP cost (standard_price convierte) |

**Custom Justech:** Sin override PO currency. Script `phase27-purchase-order-validation.py` crea fixtures DOP y USD.

---

## Factura proveedor

### Proveedor DOP

- Factura DOP → asiento CxP DOP.
- DGII 606: montos `amount_untaxed_signed`, ITBIS desde líneas.
- Sin tasa cambiaria en 606.

### Proveedor USD

- Factura USD → CxP en USD + equivalente DOP.
- `invoice_currency_rate` congelada al post.
- 606 exporta montos en **DOP** (`*_signed` y bases por línea en moneda documento convertidas según exporter).

**Código 606** (`dgii_606_exporter.py`):
- `_split_goods_services` usa `price_subtotal` en moneda factura.
- Validación RNC/NCF — sin check moneda.

---

## Pagos compra

| Flujo | Wizard | Diario |
|-------|--------|--------|
| Pago factura DOP | Hellenia payment wizard | BNKD |
| Pago factura USD | Wizard moneda USD | BNKU |
| Retenciones | Catálogo Hellenia | Convert `_convert` → DOP balance |

**Filtro moneda wizard:** Solo facturas misma moneda que pago seleccionado.

---

## DGII 609 (servicios exterior)

Único formato con columnas FX explícitas:

| Columna | Fuente |
|---------|--------|
| H Moneda | `move.currency_id.name` |
| I Tasa | `justech_do_foreign_exchange_rate` o `invoice_currency_rate` |

Validación: factura extranjera sin tasa → **error export 609**.

Campos adicionales: `justech_do_foreign_document_ref`, ISR retenido, fecha pago exterior.

---

## Asientos compra USD

Similar a ventas invertido:

| Cuenta | Efecto |
|--------|--------|
| Inventario / Gasto | Débito DOP (convertido) |
| ITBIS acreditable | Débito DOP |
| CxP proveedor | Crédito USD + DOP |

Pago posterior genera FX vía CAMBI si tasa difiere.

---

## Inventario

- `standard_price` siempre DOP.
- Recepción USD PO: Odoo convierte costo a DOP para valoración.
- Sin módulo `hellenia_inventory` en PROD v1 — stock básico Odoo.

---

## Gaps compras

1. Política moneda proveedor no en golden config YAML.
2. Campo `justech_do_foreign_exchange_rate` sin vista dedicada en formulario factura (solo review tray).
3. Sin UAT 606 con facturas compra USD publicadas post go-live.
4. Importadores: validar posición fiscal / gastos importación fuera alcance MC-1.
