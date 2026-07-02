# UAT — Informe Inventario (Bloque 6)

**Ambiente:** TEST | **Fecha:** 2026-06-30 | **Estado:** **PASS CON OBSERVACIONES**

## Verificaciones

| Prueba | Resultado |
|--------|-----------|
| Cantidad disponible | ✅ ≥ 0 |
| Entradas (recepción compra) | ✅ Validado en ciclo compras |
| Salidas (entrega venta) | ✅ Validado en ciclo ventas |
| Valoración anglosajona | ✅ Habilitada |
| Transferencias internas | Parcial — depende ubicación UAT Shelf |
| Ajustes inventario | Wizard disponible |
| Inventario físico | Pendiente procedimiento manual |
| Devoluciones | Estándar Odoo disponible |
| Reservas | Automáticas al confirmar SO |

## Estrés inventario (indirecto)

100 ventas + 100 compras ejecutadas sin inconsistencia de stock reportada.

## Pendiente

| Item | Prioridad |
|------|-----------|
| Procedimiento inventario físico | P1 |
| Política lotes/series piezas únicas | P2 |
| Reabastecimiento MTO/MTS | P3 — probablemente N/A |

**Estado:** PASS CON OBSERVACIONES

**Evidencia:** `evidence/uat-functional.json` — `block6_inventory`
