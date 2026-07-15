# Changelog — justech_managed_services

## [19.0.1.0.2] — 2026-07-15

### Corregido (pre-producción)

- Fuente única de verdad `FORM_FIELDS` en `form_schema.py` (key, etiqueta, sección, tipo, opciones).
- PDF y resumen usan etiquetas en español y valores formateados (select/multiselect/boolean).
- Porcentaje “% completado” se actualiza sin reload (barra + texto).
- Backend muestra respuestas legibles (`answers_html`) alineadas con PDF.

## [19.0.1.0.1] — 2026-07-15

### Corregido

- Navegación del botón Revisar a la sección 17.

## [19.0.1.0.0] — 2026-07-15

### Añadido

- Modelo `justech.managed.service.assessment` con secuencia `LEV-YYYY-####`.
- Formulario público website (16 secciones + revisión/envío).
- Controladores públicos con token seguro (`secrets.token_urlsafe`).
- Grupos `group_ms_user` y `group_ms_manager` con ACL y record rules.
- Smart buttons en contactos y oportunidades CRM.
- Reporte PDF QWeb, plantilla de correo y datos demo Credicefi.
- Tests `tests/test_assessment.py`.

### Notas

- Fase 1 únicamente. Sin contratos, suscripciones ni facturación recurrente.
- Desarrollo destinado a `justech_dev`; no desplegar en Producción sin autorización.
