# Impacto contable — Retenciones por factura (Fase 18)

## Principio

Las retenciones **no son descuentos**. El monto retenido se registra en cuenta contable vía `write_off_line_vals` en el pago.

## Venta (cobro cliente)

```
Banco/Caja          Neto recibido
Retención (cuenta impuesto)   Monto retenido
    Clientes (CxC)            Monto aplicado a factura
```

El pago se crea por factura con:
- `amount` = monto a aplicar − total retenido de **esa factura**
- Líneas write-off por cada retención seleccionada en la factura

## Compra (pago proveedor)

```
Proveedores (CxP)   Monto aplicado
    Banco/Caja      Neto pagado
    Retención       Monto retenido
```

## Cuentas

Tomadas de la **repartición fiscal** del impuesto `l10n_do` vinculado en el catálogo. No se inventan cuentas en el wizard.

## Conciliación

- Factura queda saldada por el monto bruto aplicado (pendiente)
- Banco refleja solo el neto transferido
- Retención en cuenta de pasivo/activo según definición l10n_do

## 606 / 607

Flags `affects_606` y `affects_607` en catálogo documentan impacto. Los reportes DGII siguen alimentándose de asientos e impuestos estándar Justech/l10n_do.
