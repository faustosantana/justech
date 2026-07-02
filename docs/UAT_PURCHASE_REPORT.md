# UAT — Informe Compras (Bloque 3)

**Ambiente:** TEST | **Fecha:** 2026-06-30 | **Estado:** **PASS CON OBSERVACIONES**

## Ciclo compras

| Paso | Verificación | Resultado |
|------|--------------|-----------|
| RFQ | PO draft/sent | ✅ |
| Orden confirmada | `purchase` | ✅ |
| Recepción | picking `done` | ✅ |
| Factura proveedor | posted | ✅ |
| NCF proveedor B11 | Asignado | ✅ |
| Pago proveedor | Registrado | ✅ |
| Reporte 606 | Líneas generadas | ✅ |
| Asiento balanceado | OK | ✅ |
| Inventario | Incremento stock | ✅ |
| Costo | standard_price aplicado | ✅ |

## Pendiente

| Item | Prioridad | Propuesta |
|------|-----------|-----------|
| Retenciones ITBIS compras | P1 | Escenario con posición fiscal en piloto |
| Aprobaciones PO | P2 | Configurar umbral con Hellenia |
| Compras internacionales | P2 | Validar si aplica |

**Estado:** PASS CON OBSERVACIONES — sin FAIL

**Evidencia:** `evidence/uat-functional.json` — `block3_purchase`
