# Validación normativa DGII — tipos emitidos vs recibidos en Compras

Fuentes:
- DGII NG 06-2018 / Guía Comprobantes Fiscales (tipos 11, 13, 14, 15, 16, 17).
- Portal DGII “Estructura y Tipos de Comprobantes”.
- Localización `l10n_do_accounting` (índice NCF, `_is_manual_document_number`, `_compute_l10n_do_fiscal_sequence`, mapa issued/received).
- Justech `PURCHASE_NCF_PREFIXES = (B11, B13, B17)` / `SALE_NCF_PREFIXES` incluye B14–B16.

## Matriz

| Tipo | Emisor según DGII | ¿Emitir desde Compras (secuencia empresa)? | ¿Solo clasificar recibido? | ¿Soportar en Motor emisión Compras? |
|---|---|---|---|---|
| **B11** | Comprador (proveedor no registrado / informal) | **Sí** — secuencia propia | No (salvo error de tipificación) | **Sí** |
| **B13** | Contribuyente (gastos menores del personal) | **Sí** — secuencia propia | No | **Sí** |
| **B14** | **Vendedor** a entidad de régimen especial | **No** | **Sí**, si el proveedor emite B14/E44 | **No** |
| **B15** | **Vendedor** al Estado | **No** | **Sí**, si el proveedor emite B15/E45 | **No** |
| **B16** | **Exportador / vendedor** al exterior | **No** | **Sí** solo si se registra un NCF ajeno (raro en compras locales) | **No** |
| **B17** | Contribuyente que paga rentas a no residente | **Sí** — secuencia propia (compra/pago exterior) | No | **Sí** |

## Odoo DO — coherencia

- Número **manual** en `in_*` excepto `informal|minor|exterior` (+ e-*): B11/B13/B17 **no** son manuales → consumen secuencia.
- Asignación automática en `in_invoice` solo para minor / informal / exterior (condiciones de partner).
- Justech: B14/B15/B16 en `SALE_NCF_PREFIXES`; B11/B13/B17 en `PURCHASE_NCF_PREFIXES`.

## Lista definitiva — tipos emitidos a soportar en Compras

1. **B11** — Comprobante de Compras  
2. **B13** — Gastos Menores  
3. **B17** — Pagos al Exterior  

**No soportar emisión desde Compras:** B14, B15, B16 (emisión = Ventas). En Compras solo pueden aparecer como **recibidos** (NCF del proveedor, sin consumir rango de la empresa).
