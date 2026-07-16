# Changelog — justech_managed_services

## [19.0.2.1.3] — 2026-07-16

### Corregido (vista Cotizaciones)

- Retirados del formulario estándar de Cotizaciones los campos Servicio Administrado y Levantamiento.
- Campos conservados en el modelo; formularios de Servicios Administrados sin cambio.
- Se mantiene el smart button «Servicio Adm.» cuando hay vínculo.

## [19.0.2.1.2] — 2026-07-15

### Corregido (datos cliente + correo)

- Snapshot desde Contactos siempre al crear (aunque exista `contact_id`); sin fallback DEMO (`000000000` / `example.invalid`).
- Botón **Actualizar desde Contactos**; el formulario público prioriza columnas snapshot sobre JSON obsoleto.
- **Preparar correo** abre composer con trazabilidad; **Enviar ahora** crea `mail.mail` y registra chatter/estado.
- Hook `mail.compose.message` marca el envío cuando el usuario confirma en el composer.
- Primera pestaña: Preparación y envío. `demo_data.xml` pasa a clave `demo` (no se instala en producción).

## [19.0.2.1.1] — 2026-07-15

### Configuración

- Menú Configuración: Plantillas, Categorías, Banco de preguntas.
- Banco de preguntas con código, descripción, obligatoriedad, uso en plantillas, filtros y duplicar.
- Preguntas como registros Odoo (sin XML embebido); plantillas solo referencian el banco.

## [19.0.2.1.0] — 2026-07-15

### UX

- Asistente Nuevo Levantamiento (cliente → preguntas → enlace → envío).
- Diseñador: categorías, preguntas, plantillas reutilizables (12 plantillas semilla).
- Formulario público dinámico según preguntas activas (fallback al formulario clásico).
- PDF corporativo con portada e índice.
- Estilos backend Justech (cards, botones, progreso).

## [19.0.2.0.1] — 2026-07-15

### Corregido (flujo creación / envío de levantamientos)

- Vista principal de Levantamientos fijada (evita abrir la ficha vacía de “Respuestas”).
- Encabezado guiado: cliente, contacto, correo, consultor, vencimiento y % completado.
- Bloque “Envío del levantamiento” con destinatario, asunto y mensaje editables.
- Botones por estado: Generar enlace, Abrir formulario, Copiar enlace/mensaje, Preparar/Enviar correo, Cancelar/Regenerar.
- Validaciones claras sin cliente, sin correo, enlace activo/vencido.
- JSON técnico solo para Administrador MS, al final.
- Copia al portapapeles vía acción backend OWL.

## [19.0.2.0.0] — 2026-07-15

### Añadido (Fase 2 operativa)

- Modelo maestro `justech.managed.service` (MS-YYYY-####) con alcance, fee, SLA básico y estados de vida.
- Flujo navegable: Levantamiento → Oportunidad → Cotización → Servicio → Fee → Ticket.
- Integración por herencia con `sale.order`, `sale_subscription`, `helpdesk.ticket`, CRM y Contactos.
- Grupos Comercial y Técnico; menú Resumen / Servicios / Levantamientos / Fees / Tickets.
- Botón Descargar PDF / Vista previa; estados comerciales del levantamiento ampliados.

### Conservado

- Formulario público Fase 1, tokens y levantamientos existentes (`managed_service_id` opcional).

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
