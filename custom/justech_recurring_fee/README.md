# Justech Fees Recurrentes

Fee = contrato/maestro periódico. No requiere cotización previa.

## Flujo

1. Crear fee (cliente, líneas, periodicidad, próxima fecha).
2. Activar.
3. Cron (diario) o «Generar ciclo ahora».
4. Por defecto: cotización en borrador vinculada al fee.
5. Revisar → confirmar → facturar (Motor Fiscal Justech al publicar).
6. Avanza la próxima fecha; el fee permanece.

## Idempotencia

Único por `fee + period_key` (`desde|hasta|tipo`). Reejecutar el cron no duplica.

## Documento a generar

- Cotización en borrador (default)
- Factura en borrador
- Factura auto-publicada (solo administradores; advertencia fiscal)

## Menú

Ventas → Fees recurrentes
