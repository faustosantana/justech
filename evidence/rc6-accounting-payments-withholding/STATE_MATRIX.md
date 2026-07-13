# Matriz de estados — pagos / facturas / banco

## Factura (`account.move.payment_state`)

| UI esperada | Valor Odoo | Significado |
|-------------|------------|-------------|
| No pagada | `not_paid` | Residual completo |
| Parcialmente pagada | `partial` | Residual > 0 y < total |
| En proceso de pago | `in_payment` | CxC conciliada con pago vía outstanding; espera banco |
| Pagada | `paid` | Residual 0 y liquidez/matched |
| Revertida | `reversed` | Nota de crédito / reverse |

## Pago (`account.payment`)

| UI | Campo | Significado |
|----|-------|-------------|
| Borrador | `state=draft` | No publicado |
| Registrado | `state=in_process` o `paid` | Asiento generado |
| Aplicado a factura | `is_reconciled=True` | Contrapartida CxC/CxP conciliada |
| Pendiente conciliación bancaria | `treasury_bank_state=bank_pending` | Outstanding/liquidez abierta |
| Conciliado con banco | `treasury_bank_state=bank_reconciled` | Outstanding conciliada con extracto |
| Cancelado | `state=canceled` | Anulado |

## Acciones UI

| Condición | Botón | Destino |
|-----------|-------|---------|
| No aplicado a factura | Aplicar a factura | Wizard / líneas CxC abiertas |
| Aplicado, banco pendiente | Conciliar con extracto bancario | `account.bank.statement.line` del diario |
| Aplicado + banco | Ver conciliación | AML ya conciliados (solo lectura) |
| Intento de re-conciliar CxC | **Bloqueado** | No abrir reconcile de líneas `reconciled=True` |
