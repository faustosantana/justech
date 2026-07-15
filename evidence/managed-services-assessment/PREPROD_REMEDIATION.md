# Remediación pre-producción — justech_managed_services Fase 1

**Fecha:** 2026-07-15  
**Entorno:** solo `justech_dev` (`erp.justech.do` / `207.244.242.58`)  
**Producción (`justgroup.app` / `31.97.6.178` / BD `justech`):** **NO tocada** — módulo `ABSENT`.  
**Rama:** `feature/managed-services-assessment`  
**Versión módulo:** `19.0.1.0.2`  
**Backup:** `/opt/odoo-dev/backups/p0-ms-preprod-remediation-20260715_192515/`

## Objetivo

Dejar Fase 1 lista para Producción corrigiendo solo pendientes funcionales:

1. PDF con todas las respuestas
2. Resumen con etiquetas legibles
3. % completado dinámico sin reload
4. Misma información en backend / resumen / PDF
5. Documentar permisos Contacto/CRM **sin** cambiar ACL globales

## Corrección aplicada

### Fuente única de verdad

`models/form_schema.py` → `FORM_FIELDS` con:

- key técnica
- etiqueta ES
- sección
- tipo (`char|text|number|select|multiselect|boolean`)
- opciones value→etiqueta
- storage (`column|json|meta`)

Derivados: `FORM_TRACKED_KEYS`, `ORG_FIELD_MAP`, `FIELD_LABELS`, `OPTION_LABELS`, `format_field_value()`, `build_sections_display()`, `compute_completion_percent()`, `labels_payload()`.

### Consumidores unificados

| Capa | Cambio |
|---|---|
| JS público | Usa `JT_MS_FIELD_LABELS` / `JT_MS_OPTION_LABELS` / `JT_MS_TRACKED_KEYS`; progreso dinámico |
| Controller | Inyecta JSON de labels |
| Modelo | `get_form_print_sections()`, `answers_html` |
| PDF QWeb | Itera `print_sections` con label/value legibles |

### Permisos Contacto/CRM

Documentado en `docs/SECURITY_CONTRACT.md` (grupos estándar mínimos).  
**Sin** `sudo()` en smart buttons, **sin** cambios a grupos fiscales ni ACL ajenas.

## Resultado por pendiente

| Pendiente | Resultado | Evidencia |
|---|---|---|
| PDF incompleto | **PASS** 16/16 | `PDF_FIELD_MATRIX.md`, `11_pdf_preprod_completo.pdf` |
| Labels técnicos | **PASS** | `12_resumen_etiquetas_legibles.png` |
| % no refresca | **PASS** 30%→32% sin reload | `13_porcentaje_dinamico.png` |
| Backend vs PDF | **PASS** misma fuente `get_form_print_sections` | answers_html + PDF |
| Permisos Contacto/CRM | **DOCUMENTADO** (sin cambio ACL) | `SECURITY_CONTRACT.md` |

## Regresión DEV (post-fix)

| # | Prueba | Resultado |
|---|---|---|
| 1–2 | Upgrade módulo a 19.0.1.0.2 | PASS |
| 3–8 | Formulario / save / resumen / submit / PDF completo | PASS |
| 9–12 | Token inválido / UI activa / link completado HTTP 200 sin traceback | PASS |
| 13–14 | Smart button opp sin duplicar | PASS |
| 15 | Permisos (contrato documentado) | PASS |
| 16–18 | sale.order / account.move / partner counts OK | PASS |
| 19–20 | `justech.do.fiscal.document.type` / `l10n_latam.document.type` legibles | PASS |
| 21–23 | Sin HTTP 500 / sin JS break en flujo público; OWL push notif ajeno | PASS |

Uninstall completo **no** reiterado (cambios sin alterar dependencias/manifest estructurales críticos; upgrade limpio).

## Archivos modificados

- `models/form_schema.py`
- `models/managed_service_assessment.py`
- `controllers/assessment_portal.py`
- `static/src/js/assessment_public.js`
- `views/website_assessment_templates.xml`
- `views/assessment_views.xml`
- `report/assessment_report.xml`
- `__manifest__.py` / `CHANGELOG.md` / `docs/SECURITY_CONTRACT.md`
- evidencia bajo `evidence/managed-services-assessment/`

## Pendientes reales residuales

1. Extracción/visual de acentos en PDF vía wkhtmltopdf en DEV puede mostrar mojibake (`MarÃa`) en algunos extractores; el contenido y etiquetas están correctos. Mitigación parcial: font DejaVu + charset meta. Validar visualmente en el visor del PDF antes de go-live.
2. Fase 2 (igualas / fees / helpdesk): fuera de alcance.

## Confirmación

- **Producción no fue tocada.**
- **No hubo merge a `main`.**
- **No se desplegó a Producción.**
- **No se implementó Fase 2.**
- **No se modificaron permisos globales/fiscales.**
