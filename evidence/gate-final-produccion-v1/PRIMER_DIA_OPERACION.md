# PRIMER_DIA_OPERACION — Justech Fiscal v1.0

Validaciones obligatorias el primer día hábil post go-live.

## Ventas

- [ ] Cotización → pedido → entrega → factura con NCF
- [ ] Tipo comprobante correcto (B01/B02 según cliente)
- [ ] Cobro y conciliación básica
- [ ] PDF / impresión sin error

## Compras

- [ ] OC → recepción → factura proveedor con NCF proveedor
- [ ] Tipo gasto DGII si aplica
- [ ] Pago a proveedor

## Pagos / Bancos

- [ ] Diario bancario operativo
- [ ] Pago abierto / aplicación si tesorería Justech está en alcance
- [ ] Retención: al menos un smoke si hay proveedores sujetos

## DGII

- [ ] Revisar bandeja/reporte 607 del día/mes
- [ ] Revisar 606 del día/mes
- [ ] Ningún bloqueo de exportación inesperado

## Centro Fiscal

- [ ] Salud Fiscal: sin críticos nuevos abiertos
- [ ] Padrón status
- [ ] Flags sin cambios no autorizados

## Cierre del día

- [ ] Conteo NCF consumidos del día vs facturas
- [ ] Escalamiento si hay >0 críticos abiertos
