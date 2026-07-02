# Certificación contable de retenciones — Fase 22

**Fecha:** 2026-07-01  
**Ambiente:** PROD

---

## Principio validado

Las retenciones **no son descuentos comerciales**. Se registran como movimiento contable independiente en cuenta de retención, reduciendo el neto transferido al banco pero manteniendo el bruto aplicado a la factura.

---

## Líneas persistentes PROD

| ID | Catálogo | Monto | Cuenta | Línea GL | Factura | Pago | affects_623 | affects_607 |
|----|----------|-------|--------|----------|---------|------|-------------|-------------|
| 18 | RET-ITBIS-30 | 540.00 | Sí | 354 | INV/00003 | PBNKD/00002 | No | Sí (ITBIS) |
| 19 | RET-GOB-5 | 500.00 | Sí | 366 | INV/00006 | PBNKD/00003 | Sí | No |

---

## Validaciones

| Criterio | Resultado |
|----------|-----------|
| Cuenta contable asignada | 2/2 |
| Línea en asiento de pago | 2/2 |
| Vinculada a factura (`move_id`) | 2/2 |
| Vinculada a pago (`payment_id`) | 2/2 |
| `partial_reconcile_id` | 2/2 válidos |
| Campo gov 623 en pago/factura (RET-GOB-5) | OK — 500.00 |
| Impacto balance (asset_current retenciones) | 5,500.00 coherente |

---

## Cadena P21 — RET-GOB-5 (certificada)

| Paso | Valor |
|------|-------|
| Base imponible | 10,000.00 |
| ITBIS 18% | 1,800.00 |
| Retención 5% gobierno | **500.00** |
| Neto transferido banco | 11,300.00 |
| Bruto aplicado factura | 11,800.00 |
| Reporte 623 | 1 válido |

---

## Cadena SMOKE — RET-ITBIS-30 (legacy)

| Paso | Valor | Nota |
|------|-------|------|
| Retención | 540.00 | ITBIS 30%, no gov |
| Campo gov factura | 500.00 | Inconsistencia datos prueba |
| 623 | Incompleto | Sin RNC + catálogo incorrecto |

**No modificar motor** — datos de prueba inconsistentes documentados en Fase 21.

---

## Veredicto retenciones

| Área | Certificado |
|------|-------------|
| Motor contable retenciones | **Sí** |
| Integración GL | **Sí** |
| Trazabilidad fiscal 623 (datos limpios) | **Sí** |
| Todos los datos PROD | **No** — 1 línea legacy incompleta |
