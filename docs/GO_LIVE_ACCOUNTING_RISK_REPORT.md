# Go-live — Riesgos contables y fiscales

**Fecha:** 2026-07-01  
**Proyecto:** Hellenia ERP  
**Fase evaluada:** 22 — Auditoría contable total

---

## Recomendación

| Decisión | Recomendación |
|----------|---------------|
| Continuar a formatos comerciales | **NO** en estado actual |
| Operar contabilidad núcleo | **Sí** con reservas documentadas |
| Declarar DGII en producción real | **Solo** tras limpiar datos maestros |

---

## Riesgos contables

| ID | Riesgo | Severidad | Mitigación |
|----|--------|-----------|------------|
| R-C1 | Base PROD es smoke — sin compras, NC, ND | **Alto** | Ejecutar escenarios 7–11 antes de go-live |
| R-C2 | INV/00003 estado `in_payment` con residual 0 | **Bajo** | Revisar/actualizar estado pago (operativo) |
| R-C3 | Sin cierre de período — P&L abierto | **Medio** | Cierre mensual antes de estados formales |

---

## Riesgos fiscales

| ID | Riesgo | Severidad | Mitigación |
|----|--------|-----------|------------|
| R-F1 | Partner SMOKE sin RNC — 5 facturas | **Alto** | Fusionar/archivar duplicados; asignar RNC |
| R-F2 | 2 líneas 623 incompletas legacy | **Medio** | Excluir o corregir datos prueba |
| R-F3 | Solo rango NCF B02 activo | **Medio** | Activar B01/B11 según operación real |
| R-F4 | Sin notas crédito — 608 no probado | **Medio** | Certificar NC antes de declarar anulados |

---

## Lo que SÍ está listo

- Motor pagos + asientos
- Motor retenciones + GL
- Reportes DGII 606/607/608/623 (motor + UI post-fix)
- Estados financieros Odoo Enterprise (apertura UI)
- Integridad: asientos cuadrados, sin huérfanos estructurales

---

## Condiciones para aprobar formatos comerciales

1. Completar matriz de 18 escenarios controlados en PROD o TEST espejo.
2. Limpiar partners duplicados y asignar RNC a entidades gubernamentales.
3. Registrar al menos: 1 compra B11, 1 NC B04, 1 ND B03.
4. Certificar export PDF/XLSX de estados financieros con supervisor contable.
5. Cerrar período piloto jun-2026 y validar carry-forward.

---

## Veredicto go-live

**NO GO** para formatos comerciales.  
**GO condicionado** para continuar desarrollo/certificación sobre base smoke existente.
