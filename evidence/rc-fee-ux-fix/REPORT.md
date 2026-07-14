# RC-FEE-UX-FIX — justech_recurring_fee 19.0.1.0.2

DEV only. Production untouched. Commit pending.

## Root cause cotización
`justech_fee_id` era visible tras `payment_term_id` sin `invisible`.

## Fix
- Cotización: smart button + pestaña solo si `justech_fee_id`.
- Fee UX: terminología, Responsable/Supervisor, plan oculto, fiscal del cliente, pedido de venta, suscripción opcional.

## Validation
ORM CLOSE_PASS — moves=2406 payments=699 GL=0.00 multiempresa 4/4.
