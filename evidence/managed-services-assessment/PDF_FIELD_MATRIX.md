# PDF / Backend / Resumen — Matriz de 16 secciones

**Entorno:** `justech_dev`  
**Registro:** `LEV-2026-0003` (`justech.managed.service.assessment` id=3)  
**URL (completado):** `https://erp.justech.do/servicios/levantamiento/RsiuLRw3lAJM-EFsjt9IpYJGTe-T3lsFA8e5r6Ztp7Y`  
**PDF:** `screenshots/11_pdf_preprod_completo.pdf` (42 501 bytes, 3 páginas)  
**Fuente de verdad:** `custom/justech_managed_services/models/form_schema.py` → `FORM_FIELDS`

## Causa raíz del mismatch previo

No era un rename inconsistente de keys HTML↔schema. Las keys ya coincidían.

El PDF incompleto / resumen técnico se debía a:

1. Ausencia de `JT_MS_FIELD_LABELS` / mapas de opciones (se mostraban keys crudas).
2. PDF QWeb usaba `t-if="val"` + etiqueta `key` técnica y variable `data` frágil.
3. En UAT anterior algunos valores de prueba se enviaron con codes incorrectos (automatización), no con el `name=` real del HTML.

## Matriz (PASS = sección con respuestas legibles en backend print sections ≡ PDF)

| Sección | Respuesta enviada (muestra) | Backend | Resumen* | PDF | Resultado |
| --- | --- | --- | --- | --- | --- |
| 1. Información de la organización | Credicefi / María Preprod / RNC | 7 filas | etiquetas ES | presente | **PASS** |
| 2. Usuarios | 51 a 100 / 75 / Híbrida | 3 | ES | presente | **PASS** |
| 3. Oficinas y ubicaciones | 3 / SD-Santiago / Parcialmente | 3 | ES | presente | **PASS** |
| 4. Equipos tecnológicos | 40 desktops… Dell, HP… | 9 | ES | presente | **PASS** |
| 5. Plataformas y servicios | M365, Azure… Odoo Justech | 4 | ES | presente | **PASS** |
| 6. Servicios a tercerizar | Mesa de ayuda, Soporte remoto, Otro | 1 | ES | presente | **PASS** |
| 7. Niveles de soporte | Nivel 1, 2, 3 | 1 | ES | presente | **PASS** |
| 8. Horario de cobertura | Personalizado 07:00–19:00 | 5 | ES | presente | **PASS** |
| 9. Modalidad del servicio | Rec. Justech / 2× mes | 2 | ES | presente | **PASS** |
| 10. Volumen de soporte | 51–100 / Contraseñas… | 2 | ES | presente | **PASS** |
| 11. Soporte actual | Mixto / Jira / Sí-No | 7 | ES | presente | **PASS** |
| 12. Prioridades y SLA | 1 hora / sin internet… | 3 | ES | presente | **PASS** |
| 13. Seguridad y cumplimiento | Políticas… NDA Sí | 5 | ES | presente | **PASS** |
| 14. Objetivo de la tercerización | Tiempos, especialistas… | 1 | ES | presente | **PASS** |
| 15. Inicio y presupuesto | 30 días / RD$ 120,000 | 3 | ES | presente | **PASS** |
| 16. Comentarios finales | Texto remediación preprod | 1 | ES | presente | **PASS** |

\* Resumen público validado en fixture UI `LEV` id=4 con etiquetas: `screenshots/12_resumen_etiquetas_legibles.png` (sin keys técnicas).

**Resultado global:** 16/16 **PASS**.

## Verificaciones negativas

- No aparecen labels = keys técnicas en backend HTML ni en resumen.
- PDF texto extraído contiene valores legibles (`Dell`, `Soporte remoto`, `Jira Service Management`, `RD$ 120,000`).
- Keys técnicas `employee_count_range` / option code `soporte_remoto` **no** aparecen como etiquetas.
