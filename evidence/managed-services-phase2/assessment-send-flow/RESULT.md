# Resultado — Flujo creación y envío de levantamientos

**Fecha:** 2026-07-15  
**Entorno:** `justech_dev` / https://erp.justech.do  
**Producción:** módulo `justech_managed_services` **ABSENT**  
**Rama:** `feature/managed-services-phase2`  
**Versión módulo:** `19.0.2.0.1`  
**Backup:** `/opt/odoo-dev/backups/p2-assessment-send-20260715_213520/justech_dev.dump`

## Causa raíz (ficha “vacía”)

La vista secundaria `view_justech_managed_service_assessment_answers_form` competía como form por defecto (misma prioridad). Al pulsar **Nuevo** se abría la ficha de respuestas (casi vacía, `create="0"`).

**Corrección:** prioridad form principal = 1, respuestas = 999, y `ir.actions.act_window.view` amarra list+form correctos.

## DEMO principal

| Campo | Valor |
|---|---|
| Referencia | **LEV-2026-0008** |
| ID | 8 |
| Cliente | Credicefi (1963) |
| Contacto | Contacto DEMO Credicefi (1965) |
| Correo | `contacto.credicefi.demo@example.invalid` |
| Teléfono | 809-555-0100 |
| Consultor | Fausto Santana |
| Estado | Enviado |
| Ficha | https://erp.justech.do/odoo/justech.managed.service.assessment/8 |
| Enlace público | https://erp.justech.do/servicios/levantamiento/7ega0RZjEUlGx9F5jNH8lzt4he7cRACKIK7pZus1DiQ |

### DEMO sin correo (copia manual)

| Campo | Valor |
|---|---|
| Referencia | **LEV-2026-0009** |
| Contacto | Contacto Sin Correo DEMO |
| Resultado | Enlace generado + advertencia de sin correo |

## Pruebas

| # | Prueba | Resultado |
|---|---|---|
| 1 | Nuevo abre form completo (cliente, contacto, envío) | PASS |
| 2–5 | Credicefi + contacto + título auto + guardar | PASS |
| 6–8 | Generar enlace visible, estado Enviado | PASS |
| 9 | Abrir formulario (URL pública) | PASS (botón) |
| 10 | Copiar enlace (clipboard action) | PASS (acción JS) |
| 11 | Copiar mensaje | PASS (acción JS + texto share) |
| 12–13 | Preparar correo → composer con destinatario/asunto/cuerpo | PASS (no Enviar) |
| 14 | No enviar correo real | PASS (`mails_created=0`) |
| 15 | Chatter registra generación de enlace | PASS |
| 16 | Sin cliente no genera enlace | PASS |
| 17 | Sin correo sí genera + advertencia | PASS |
| 18 | Pestaña Técnico solo `group_ms_manager` | PASS (vista) |
| 19 | Producción no tocada | PASS |

## Archivos modificados

- `custom/justech_managed_services/models/managed_service_assessment.py`
- `custom/justech_managed_services/views/assessment_views.xml`
- `custom/justech_managed_services/static/src/js/assessment_clipboard.js` *(nuevo)*
- `custom/justech_managed_services/data/mail_template.xml`
- `custom/justech_managed_services/__manifest__.py`
- `custom/justech_managed_services/CHANGELOG.md`

## Capturas

- `01_nuevo.png`
- `03_lev_0008_ficha.png`
- `05_bloque_envio.png`
- `06_composer_correo.png`
- `uat_result.json`

## Confirmaciones

- Correos reales enviados en esta prueba: **0**
- Facturas: no tocadas
- Merge / despliegue Producción: **no realizados**
- Alcance: solo UX de creación/envío de levantamientos (sin facturación auto, SLA, horas ni reportes)
