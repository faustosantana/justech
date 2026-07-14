# Changelog

## 19.0.1.0.1

- Filtro de impuestos por empresa al generar documentos (fix multiempresa).
- Savepoint al generar ciclo (sin cotizaciones/facturas huérfanas).
- Lock advisory + FOR UPDATE en cron.
- Wizard de reactivación (conservar o reprogramar fecha).
- Auditoría de cambios de línea en chatter.
- ACL de creación de ciclos para usuarios Fee.
- Filtro «Próximos 7 días».
- Cierre validado en DEV: fee maestro, idempotencia, NCF Justech, multiempresa 4/4.

## 19.0.1.0.0

- Modelo maestro `justech.recurring.fee` + líneas + ciclos.
- Generación de cotización / factura borrador / factura auto (admin).
- Cron diario idempotente.
- Vínculos en `sale.order` y `account.move`.
- Menú Ventas → Fees recurrentes.
