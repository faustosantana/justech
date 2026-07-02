# Limpieza PDF factura — Fase 17.1

## Cambios (`hellenia_reports` v19.0.1.0.1)

### Eliminado
- Código QR (no e-CF)
- Título "Proforma Invoice"
- Bloque NCF duplicado de `justech_l10n_do_ncf`
- Textos en inglés: Customer Code, Reference, Untaxed Amount, Payment Communication, Invoice Date, Due Date

### Títulos dinámicos (método `hellenia_fiscal_document_title()`)

| Prefijo NCF | Título PDF |
|-------------|------------|
| B01 | FACTURA DE CRÉDITO FISCAL |
| B02 | FACTURA DE CONSUMO |
| B03 | NOTA DE DÉBITO |
| B04 | NOTA DE CRÉDITO |

### Bloque fiscal

```
Número de Comprobante Fiscal
B0100000000
Válido para crédito fiscal conforme a la DGII.
Factura de Crédito Fiscal
```

Para B02:
```
Comprobante de consumo no válido para crédito fiscal.
```

### Etiquetas español

Cliente, Fecha de factura, Fecha de vencimiento, Subtotal, Concepto de pago, Descripción, Cantidad, etc.

## Archivos

- `custom/hellenia_reports/models/account_move.py`
- `custom/hellenia_reports/report/report_invoice.xml`
- `custom/hellenia_reports/static/src/scss/hellenia_reports.scss`
