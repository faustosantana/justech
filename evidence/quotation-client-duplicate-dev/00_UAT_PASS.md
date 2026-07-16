# UAT DUPLICIDAD DE CLIENTE EN COTIZACIONES — PASS (DEV)

## Entorno
- Dominio: erp.justech.do
- Host: 207.244.242.58
- DB: justech_dev
- Servicio: odoo-dev.service
- Conf: /opt/odoo-dev/conf/odoo-dev.conf

## Backup
`/opt/odoo-backups/quotation-client-duplicate-dev-20260716_104555/`
Restore test: PASS (temp DB views=4822, sale_orders=734)

## Corrección
| Campo | Valor |
|---|---|
| Módulo | `justech_quotation_client_dedup` 19.0.1.0.0 |
| Archivo | `custom/justech_quotation_client_dedup/report/sale_report_templates.xml` |
| XML ID | `justech_quotation_client_dedup.report_saleorder_document_hide_header_address` |
| inherit_id | `sale.report_saleorder_document` |
| priority | 99 |
| xpath | `//t[@t-set='address']` position=`replace` → `<t t-set="address" t-value="False"/>` |

## Intactos
- `web.external_layout_bubble` (hash igual al backup)
- `web.address_layout` (hash igual al backup)
- `#informations` / `customer_info`

## Cotizaciones
| Empresa | SO | Antes | Después |
|---|---|---|---|
| Justech | C-0003891 | duplicado Credicefi | 1 bloque Cliente |
| PlugSafe | CPS-0000099 | duplicado Capital Dbg | 1 bloque + RNC |
| Just Office | CJO-0000602 | duplicado Consorcio + RNC | 1 bloque + RNC |
| Omni | COS-0000082 | duplicado Instituto + RNC | 1 bloque + RNC |

## Regresión DEV
- Factura cliente FC/2026/00373: OK (NCF presente)
- Factura proveedor FP/2026/06/0108: OK
- OC P00168: OK
- OV confirmada CJO-0000600: OK (mismo reporte sale; sin duplicado)
- Entrega JT/IN/00136: OK
- Pago PBNK1/2026/00212: OK
- Proforma C-0003891: OK

## Producción
No modificada.
