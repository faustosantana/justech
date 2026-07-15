# MANUAL UAT — justech_managed_services (Fase 1)

**Entorno:** `erp.justech.do` / BD `justech_dev` (`207.244.242.58`)  
**Producción (`justgroup.app` / `31.97.6.178` / BD `justech`):** **NO modificada** (módulo `ABSENT`).  
**Fecha:** 2026-07-15  
**Rama:** `feature/managed-services-assessment`  
**Backup fresco previo:** `/opt/odoo-dev/backups/p0-ms-uat-manual-20260715_201527/` (dump + filestore; restore test PASS)

## URL de prueba (post-reinstall fixture)

`https://erp.justech.do/servicios/levantamiento/oeKCDagkiByGNBRtig3Iznt5x_ug4hYLq73bEWgBFg8`  
(Referencia: `LEV-2026-0002` — Credicefi DEMO DEV)

> El UAT completo del flujo público se ejecutó sobre `LEV-2026-0006` **antes** del ciclo uninstall/reinstall (ese registro quedó en backup; tras reinstall se recreó fixture activo arriba).

## 1. Formulario público Credicefi — resultado

| # | Paso | Resultado |
|---|---|---|
| 1 | Abrir enlace sin autenticación | PASS |
| 2 | Logo Justech, título, cliente Credicefi, diseño corporativo | PASS |
| 3 | Completar varias secciones | PASS |
| 4 | Guardar y continuar | PASS (`state=in_progress`, `completion_percent` > 0) |
| 5–7 | Cerrar / reabrir mismo enlace / respuestas permanecen | PASS (p.ej. `org_responsible=María UAT`, `qty_desktop=40`) |
| 8 | Completar 16 secciones | PASS (datos JSON persistidos; 57 claves) |
| 9 | Resumen final (Revisión) | PASS tras corrección JS (ver errores) |
| 10 | Enviar | PASS → `state=done` |
| 11 | Completado | PASS (`completion_percent=100`, `link_active=False`) |
| 12 | Ya no permite edición pública | PASS (página “Enlace no disponible / ya fue enviado”) |
| 13 | Backend muestra respuestas | PASS (form `LEV-2026-0006`, pestaña Organización / respuestas) |
| 14–15 | Generar/revisar PDF con secciones | PASS parcial (PDF 27 859 bytes; 16 secciones listadas; ver pendientes) |

### Capturas

Ver `screenshots/`:

- `01_desktop_inicial.png`
- `02_seccion_intermedia_equipos.png`
- `04_revision.png`
- `05_confirmacion_final.png`
- `06_ya_completado.png`
- `08_pdf_levantamiento.pdf` + `08_pdf_pagina1.png` + `08_pdf_text.txt`
- `10_backend_form_completado.png`

## 2. Errores públicos

| Caso | Resultado | Captura |
|---|---|---|
| Token inválido | PASS — branding Justech, sin traceback/500/IDs | `07_error_token_invalido.png` |
| Enlace vencido | PASS | `07b_error_vencido.png` |
| Enlace inactivo | PASS | `07c_error_inactivo.png` |
| Cancelado | PASS | `07d_error_cancelado.png` |
| Ya completado | PASS | `06_ya_completado.png` |

Sin exposición de datos de cliente en páginas de error.

## 3. Smart buttons

| Origen | Contador | Dominio | Resultado |
|---|---|---|---|
| Contacto Credicefi (`res.partner` 1957) | 7 (pre-uninstall) / acción filtra `partner_id` | Solo Credicefi | PASS vía shell |
| CRM oportunidad 282 | 1 | `opportunity_id=282` | PASS |
| Crear oportunidad 2× | Misma `res_id` | No duplica | PASS |

**Nota UI:** usuario `uat_ms_manager` no puede abrir formulario de Contacto/CRM completo por `AccessError` fiscal `justech.do.fiscal.document.type` (preexistente / fuera de alcance MS). Smart buttons validados por dominio y contadores en shell. No se modificaron grupos generales.

## 4. Permisos (check_access)

| Perfil | Resultado |
|---|---|
| Administrador MS (`uat_ms_manager`) | Crear/editar/reabrir/revisar/PDF/oportunidad — PASS |
| Usuario MS (`uat_ms_user`) | Lee asignado (rec 6); **no** lee no asignado (rec 11); **no** unlink — PASS |
| Sin grupo (`uat_ms_bare`) | Sin acceso modelo; menú filtrado invisible (`_filter_visible_menus` vacío) — PASS |

## 5. Corrección aplicada durante UAT

- Bug: botón **Revisar** navegaba a sección 16 en vez de 17.  
- Fix: `static/src/js/assessment_public.js` → `showSection(SECTION_COUNT)`.  
- Versión módulo: `19.0.1.0.1`.

## 6. Pendientes reales (no bloquean cierre Fase 1 técnico)

1. Resumen público muestra claves técnicas (`org_company_name`) si falta `JT_MS_FIELD_LABELS`.
2. Etiqueta “% completado” del HTML no se refresca en cliente hasta reload (barra sí).
3. PDF lista las 16 secciones; algunas respuestas quedan vacías si el submit no normalizó todos los nombres de campo del formulario.
4. Usuario solo-MS no abre Contacto/CRM por ACL fiscal ajeno (documentado; no se elevaron grupos globales).

## Confirmación

- **Producción no fue tocada.**
- **No hubo merge a `main`.**
- **No se desplegó a Producción.**
- **No se implementó Fase 2.**
