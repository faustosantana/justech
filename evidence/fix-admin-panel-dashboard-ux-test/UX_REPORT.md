# UX Report — Panel Administrar personalización (Dashboard)

**Fecha:** 2026-07-07  
**Versión:** justech_modules 19.0.1.8.2 · justech_admin 19.0.2.13.0

## Cambio visual

El panel **Administrar personalización** pasó de formulario/lista Odoo a **dashboard moderno**:

| Antes | Ahora |
|-------|-------|
| Tabla de funciones | Kanban por sección con tarjetas |
| Grupos Odoo estándar | KPI badges (Estado, Pagado, Licencia, Empresas, Funciones, Modificación) |
| Lista de empresas | Chips visuales ☑ |
| Auditoría técnica | Timeline legible (“Usuario activó B01…”) |
| Footer plano | Barra de acciones primarias + peligrosas (outline-danger) |

## Secciones Fiscal RD

- **COMPROBANTES** — B01, B02, B03, B04, NCF, Secuencias
- **DGII** — 606, 607, 623
- **IMPUESTOS** — ITBIS, Retenciones
- **VALIDACIONES** — Validaciones fiscales RD

## Modal

- Ancho hasta 1120px (96vw)
- Grid responsivo 3 → 2 → 1 columnas en tarjetas de función

## Lógica

Sin cambios en NCF/DGII/POS/PDF. Switches = control comercial (`justech.client.module.feature.flag`).

## Validación

- TEST: 67/67 tests PASS · validation PASS · healthcheck PASS
- PROD: validation PASS · backup `fix-admin-panel-dashboard-ux-2026-07-07_072123.dump` · healthcheck PASS

## Verificación visual recomendada

1. Configuración → Justech → Módulos del Cliente
2. Administrar en **Fiscal RD / NCF / DGII**
3. Confirmar KPIs arriba, secciones agrupadas, switches en tarjetas
