# Revisión fiscal DGII — documentos visibles

## Flujo guardado (no temporal)

1. **Contabilidad → Reportes → Reportes DGII → Generar 606**
2. Indicar período `YYYYMM` (ej. `202606`)
3. **Validar período** — resumen y contadores
4. **Guardar revisión** — crea `justech.do.fiscal.report` persistente
5. Abrir desde **Revisión fiscal** en cualquier momento

## Pestañas por estado

| Pestaña | Contenido |
|---------|-----------|
| Todos los documentos | Facturas completas del período |
| Válidos para exportar | Listos para Excel DGII |
| Incompletos | Errores fiscales pendientes |
| Excluidos | Marcados `justech_do_include_in_dgii = False` |
| Anulados | NCF anulados |
| Requieren aprobación | Exclusiones manuales pendientes |

## Columnas por línea

Documento, tipo documento, cliente/proveedor, RNC/cédula, tipo identificación, NCF, NCF modificado, fecha, moneda, total, ITBIS, retenciones, estado fiscal, motivo exclusión, usuario/fecha exclusión, aprobado por, fecha aprobación.

## Regla clave

**Ningún documento del período queda fuera de la revisión.** Las exclusiones automáticas (UAT/demo) aparecen en la pestaña Excluidos con motivo visible y bitácora.
