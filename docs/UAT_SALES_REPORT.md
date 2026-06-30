# UAT — Informe Ventas (Bloques 2, 4, 5)

**Ambiente:** TEST | **Fecha:** 2026-06-30 | **Estado:** **PASS CON OBSERVACIONES**

## Ciclo ventas (Bloque 2)

| Paso | Verificación | Resultado |
|------|--------------|-----------|
| Cotización | SO estado draft | ✅ |
| Pedido confirmado | estado `sale` | ✅ |
| Reserva inventario | picking assigned | ✅ |
| Entrega | picking `done` | ✅ |
| Factura publicada | posted | ✅ |
| NCF B01 | Asignado automático | ✅ |
| PDF factura | Generado (>1 KB) | ✅ |
| Cobro | Pago registrado | ✅ |
| Conciliación CxC | `paid`/`in_payment` | ✅ |
| Reporte 607 | Líneas generadas | ✅ |
| Asiento balanceado | Débito = Crédito | ✅ |
| ITBIS | Líneas impuesto | ✅ |

**Observación:** Conciliación bancaria formal pendiente validación contador.

## Notas de crédito (Bloque 4)

| Prueba | Resultado |
|--------|-----------|
| NC total B04 | ✅ |
| Asiento balanceado | ✅ |
| Reporte 608 (void) | ✅ |
| NC parcial | Pendiente wizard manual |

**Estado:** PASS CON OBSERVACIONES

## Notas de débito (Bloque 5)

| Prueba | Resultado |
|--------|-----------|
| ND B03 desde factura | ✅ |
| Inclusión en flujo 607 | ✅ |

**Estado:** PASS

## Evidencia

`evidence/uat-functional.json` — `block2_sales`, `block4_credit_notes`, `block5_debit_notes`
