# Reporte de validación de datos de prueba — Fase 13.7

**Fecha:** 2026-06-29  
**Base de datos:** `hellenia_test`  
**Script:** `scripts/phase13-7-validate-test.py`

---

## Resumen

| Métrica | Valor |
|---------|-------|
| Clientes creados/asegurados | 10 |
| Proveedores creados/asegurados | 5 |
| Productos creados/asegurados | 20 |
| Quants con existencia | 16 |
| Errores de validación | 0 |
| Advertencias | 0 |

---

## Clientes (10)

Prefijo: `Cliente Prueba F137-XX`  
Cada registro incluye RNC ficticio (`1XX000000X`), tipo contribuyente y posición fiscal RD.

Uso en flujo: cliente principal `Cliente Prueba F137-01` en cotización S00016.

---

## Proveedores (5)

Prefijo: `Proveedor Prueba F137-XX`  
RNC ficticio y datos fiscales RD.

Uso en flujo: `Proveedor Prueba F137-01` en orden P00010.

---

## Productos (20)

Prefijo: `Producto Prueba F137-XX`  
- Tipo: almacenable (`product`)  
- Precio venta y costo configurados  
- Categoría: All / Saleable  
- Stock inicial vía `stock.quant` + `action_apply_inventory`

---

## Rangos NCF de prueba

| Tipo | Secuencia | Uso validado |
|------|-----------|--------------|
| B01 | Factura cliente | B0100020001 |
| B02 | (reservado) | — |
| B03 | Nota débito | B0300020018 |
| B04 | Nota crédito | B0400020018 |

Rangos gestionados por `justech_l10n_do_ncf` / secuencias fiscales RD.

---

## Flujo documental generado

| Documento | Número | Monto referencia |
|-----------|--------|------------------|
| Cotización | S00016 | Con ITBIS 18% |
| Factura | INV/2026/00119 | Posted + NCF |
| Cobro | PBNK1/2026/00104 | Conciliado |
| NC | B0400020018 | Posted |
| ND | B0300020018 | Posted |
| OC | P00010 | Confirmada |
| Factura proveedor | FACTU/2026/06/0105 | Posted |
| Pago proveedor | PBNK1/2026/00105 | Posted |

---

## Validaciones contables e inventario

- **Balance:** cuadre contable verificado (`accounting_balance: true`)
- **ITBIS:** línea con impuesto 18% en factura de venta
- **Stock:** movimientos de entrega y recepción sin error fatal; entrega en estado `assigned` (reserva válida)

---

## Reportes fiscales

| Reporte | Acción | Estado |
|---------|--------|--------|
| 606 | `justech_l10n_do_ncf.action_606_report` | OK |
| 607 | `justech_l10n_do_ncf.action_607_report` | OK |
| 608 | `justech_l10n_do_ncf.action_608_report` | OK |

---

## Evidencia machine-readable

```json
{
  "ok": true,
  "test_data": { "customers": 10, "vendors": 5, "products": 20 },
  "validations": {
    "tax_18_sale": true,
    "invoice_ncf": true,
    "accounting_balance": true,
    "stock_quants": 16
  }
}
```

Archivo completo: `evidence/phase13-7-test-functional-validation.json`

---

## Conclusión

Datos ficticios y flujo completo **certificados en TEST**. Listos como baseline para regresión en futuras fases.
