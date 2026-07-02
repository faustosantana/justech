# Fase 19 — Exportador piloto DGII 606

## Ubicación

| Componente | Ruta |
|------------|------|
| Servicio exportador | `custom/justech_l10n_do_reports/models/dgii_606_exporter.py` |
| Mapeo normativo | `custom/justech_l10n_do_reports/data/dgii_606_mapping.json` |
| Origen mapeo repo | `data/localizations/do/mappings/dgii_606.json` |
| Wizard | `custom/justech_l10n_do_reports/wizard/fiscal_report_wizard.py` |
| Historial | `justech.do.fiscal.report` |

## Menú Odoo

```
Contabilidad → Reportes → Reportes DGII → Generar 606
```

Acciones disponibles en el wizard:

1. **Validar** — ejecuta validaciones sin generar archivo
2. **Generar Excel 606** — valida, crea historial, exporta Excel DGII y descarga
3. **Guardar historial** — genera líneas en `justech.do.fiscal.report` sin descargar

## Layout Excel generado

Replica la hoja **Herramienta Formato 606** según mapeo NG 07-2018:

- Encabezado: RNC compañía, período YYYYMM, cantidad registros
- Fila 11: encabezados oficiales (columnas A–AA)
- Fila 12+: datos de compras

### Columnas exportadas

| Col | Campo DGII | Fuente Odoo |
|-----|------------|-------------|
| A | Líneas | Secuencia |
| B | RNC o Cédula | `partner.justech_do_clean_vat()` |
| C | Tipo Id | `partner.justech_do_partner_id_type` |
| D | Tipo bienes/servicios | Default `02` (P1 pendiente) |
| E | NCF | `move.justech_do_ncf` |
| F | NCF modificado | `move.justech_do_ncf_modified` |
| G | Fecha comprobante | `invoice_date` YYYYMMDD |
| I | Fecha pago | Último pago en período |
| K/L | Servicios / Bienes | Líneas por `product.type` |
| M | Total facturado | `amount_untaxed` |
| N | ITBIS facturado | Líneas impuesto ITBIS |
| O | ITBIS retenido | Retenciones catálogo ITBIS |
| T | Tipo retención ISR | `dgii_withholding_code` |
| U | Monto retención renta | Retenciones ISR |
| Z | Forma de pago | Inferida de `payment_state` |
| AA | Estatus | `justech_do_dgii_line_status` |

Columnas P–S, V–Y en cero en piloto (campos P2 pendientes).

## Validaciones (español)

Errores bloqueantes antes de exportar:

- Proveedor sin RNC/Cédula
- Proveedor sin tipo de identificación
- Factura sin NCF
- Fecha fuera del período
- Impuesto positivo no clasificado (no ITBIS/ISC)
- Retención con `affects_606` sin `dgii_withholding_code`

## Dependencias

- `xlsxwriter` (declarado en `__manifest__.py`)
- `hellenia_account` (catálogo retenciones)

## Fuentes de datos

- `account.move` — facturas proveedor `in_invoice`, `in_refund`
- `account.move.line` — impuestos y retenciones
- `res.partner` — RNC, tipo identificación
- `account.payment` — fecha y forma de pago
- `hellenia.withholding.catalog` — códigos DGII retenciones

## Formato de salida

- Archivo: `DGII_606_YYYYMM.xlsx`
- Guardado en `justech.do.fiscal.report.export_file` (historial)

## Limitaciones del piloto

- Tipo bienes/servicios (col D): default `02` hasta campo P1 `justech_do_expense_type_606`
- Forma de pago (col Z): inferida, no campo dedicado P1
- ITBIS proporcionalidad, ISC, propina: columnas en cero
- Archivo `.xlsx` (no `.xls` con macros DGII) — estructura de columnas conforme
