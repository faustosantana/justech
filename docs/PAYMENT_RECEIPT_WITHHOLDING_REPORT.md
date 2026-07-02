# Recibo de pago con retenciones

## Plantilla

`hellenia_account/reports/payment_receipt_withholding_templates.xml` hereda `account.report_payment_receipt_document`.

## Contenido agregado

- Total aplicado a factura(s)
- Total retenido
- Neto recibido/pagado
- Tabla por línea: Factura, NCF, Retención, Base, %, Monto retenido

## Ejemplo renderizado

```
Detalle de aplicación y retenciones
Total aplicado a factura(s)     RD$11,800.00
Total retenido                  RD$ 2,300.00
Neto recibido/pagado            RD$ 9,500.00

Retenciones por factura
Factura    NCF           Retención        Base        %     Monto
INV/...    B0100020034   ITBIS 100%       1,800.00   100%  1,800.00
INV/...    B0100020034   Gobierno 5%     10,000.00     5%    500.00
```

## Acceso

Desde el pago registrado → Imprimir → Recibo de pago (`account.action_report_payment_receipt`).
