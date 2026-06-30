# Bandeja de revisión fiscal DGII en línea

## Menú

**Contabilidad → Reportes → Reportes DGII → Revisión fiscal**

## Flujo

1. Crear reporte (606/607/608) con período.
2. **Cargar período** — tabla con todos los documentos.
3. **Validar período** — clasificación fiscal y resumen.
4. Revisar líneas: filtros válidos / incompletos / excluidos / anulados.
5. **Excluir** documentos con motivo obligatorio (si aplica).
6. **Enviar a aprobación** (automático al excluir manualmente).
7. Supervisor **aprueba** o **rechaza**.
8. Supervisor **genera Excel DGII** (solo documentos válidos incluidos).

## Columnas de la tabla

Incluir, Estado fiscal, Documento, Tipo, NCF, NCF modificado, Contacto, RNC/Cédula, Fecha, Vencimiento, Moneda, Total, ITBIS, Retenciones, Forma de pago, Motivo exclusión, Aprobado por, Fecha aprobación.

## Modelos (reutilizados)

| Concepto 19.3 | Modelo Odoo |
|---------------|-------------|
| `dgii.report.run` | `justech.do.fiscal.report` |
| `dgii.report.line` | `justech.do.fiscal.report.line` |
| `dgii.report.approval` | `justech.do.dgii.report.approval` |
| `dgii.report.audit` | `justech.do.dgii.report.audit` |

## Extensibilidad 607/608/609/623

La carga de líneas usa `_collect_review_lines()` por tipo de reporte. 606 tiene clasificación completa; 607/608 cargan estructura equivalente para revisión futura.
