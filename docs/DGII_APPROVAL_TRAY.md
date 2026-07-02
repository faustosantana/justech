# Bandeja global — Pendientes de aprobación DGII

## Menú

**Contabilidad → Reportes → Reportes DGII → Pendientes de aprobación** (supervisores)

## Comportamiento

- Bandeja de trabajo global, no un reporte independiente
- Muestra todos los reportes DGII (606, 607, 608, 609, 623 y futuros) con documentos pendientes
- Dominio: `approval_ids.state = pending`

## Columnas de la bandeja

| Columna | Campo |
|---------|-------|
| Tipo de reporte | `report_type` |
| Período | `period_code` |
| Empresa | `company_id` |
| Enviado por | `approval_submitted_by_id` |
| Fecha envío | `approval_submitted_at` |
| Documentos pendientes | `pending_approval_count` |
| Estado | `state` |

## Al abrir un registro

Solo documentos pendientes de decisión, con acciones:

- Aprobar exclusión (por línea o todas)
- Rechazar exclusión
- Solicitar corrección
- Abrir factura
- Ver PDF
- Consultar bitácora

## Salida automática de la bandeja

Cuando todos los documentos están aprobados o rechazados/corregidos, el reporte desaparece de **Pendientes de aprobación** y queda en **Historial fiscal**.
