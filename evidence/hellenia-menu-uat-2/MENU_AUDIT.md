# HELLENIA-MENU-UAT-2 — Auditoría de menús Contabilidad (PROD)

**Base de datos:** `hellenia_prod`  
**Fecha:** 2026-07-09  
**Módulo desplegado:** `hellenia_ui` 19.0.1.0.10

## Comparativa

| Fuente | Hallazgo principal |
|---|---|
| Odoo 19 EE estándar | Estructura anidada: Clientes/Proveedores/Pagos/Contabilidad/Revisión/Reportes/Configuración |
| Justgroup / Hellenia pre-UAT2 | Asientos y Apuntes duplicados en raíz + Operaciones contables; DGII bajo Reportes; NCF/Retenciones bajo Configuración |
| Personalizaciones Justech | Auditoría Fiscal, Pagos abiertos, DGII, Conduces, Retenciones — conservadas |

## Duplicidades detectadas (antes)

1. **Asientos contables** y **Apuntes contables** en raíz y bajo Operaciones contables.
2. **Operaciones contables** vs **Contabilidad** (mismo contenedor EE renombrado).
3. **Pagos** en Clientes/Proveedores sin hub central de tesorería.
4. **Conciliar apuntes** (nombre inventado) vs estándar Odoo **Conciliar**.
5. **Reportes DGII** bajo Reportes y **Auditoría Fiscal** como raíz separada con solapamiento NCF.
6. **NCF / Retenciones** bajo Configuración y también bajo Auditoría Fiscal (accesos dispersos).
7. Contenedores vacíos visibles: Cierre, Transacciones, Activos y pasivos.

## Decisiones

- Un solo hub **Contabilidad** (`menu_finance_entries`) con asientos/apuntes/activos/préstamos/conciliar/bloqueos.
- Hub **Pagos** nuevo con conciliación bancaria estándar.
- **Auditoría Fiscal** concentra DGII + NCF + Retenciones.
- **Declaración fiscal** EE bajo Reportes > Impuestos (no duplicar en Contabilidad).
- Ocultar contenedores intermedios vacíos (no eliminar xmlids).
