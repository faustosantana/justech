# Bitácora auditoría DGII

## Modelo `justech.do.dgii.report.audit`

Registra en el reporte:

| Evento | Cuándo |
|--------|--------|
| `validate` | Carga / validación período |
| `exclude` | Exclusión manual con motivo |
| `include` | Re-inclusión tras rechazo |
| `submit_approval` | Envío a supervisor |
| `approve` | Aprobación exclusiones |
| `reject` | Rechazo exclusiones |
| `generate` | Excel DGII generado (+ hash SHA-256) |
| `reopen` | Reapertura por supervisor |

## Campos por evento

- Usuario (`user_id`)
- Documento (`move_id`) si aplica
- Línea (`line_id`) si aplica
- Descripción
- Hash y nombre de archivo (generación)

## Chatter

- `account.move`: exclusión / re-inclusión
- `justech.do.fiscal.report`: validación, exclusiones, aprobación, generación

## Excel generado

`export_file_hash` en el reporte = SHA-256 del archivo binario exportado.
