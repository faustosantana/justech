# Exclusiones DGII — auditoría visible

## Exclusión manual

1. Usuario selecciona línea → **Excluir de DGII**
2. Motivo obligatorio
3. Registro: usuario, fecha/hora, chatter documento y reporte
4. Estado → **Requiere aprobación** (supervisor)
5. Bitácora `justech.do.dgii.report.audit` evento `exclude`

## Exclusión automática (UAT/demo)

Permitida solo si:

- El documento **permanece visible** en pestaña Excluidos
- Tiene motivo (ej. «Documento de prueba/UAT excluido del reporte fiscal.»)
- Queda en bitácora al cargar revisión
- El usuario puede revisarlo antes de exportar

No se altera contabilidad ni se borran facturas.

## Campos en línea de revisión

| Campo | Uso |
|-------|-----|
| `auto_exclusion` | Exclusión previa al reporte (UAT/sistema) |
| `manual_exclusion` | Exclusión propuesta en esta revisión |
| `exclusion_reason` | Motivo visible |
| `excluded_by_id` / `excluded_at` | Trazabilidad manual |

## Excel final

Solo documentos **válidos e incluidos**, con exclusiones manuales **aprobadas** por supervisor.
