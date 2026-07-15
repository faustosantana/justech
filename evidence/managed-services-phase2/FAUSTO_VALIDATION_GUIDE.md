# Guía de validación funcional — Fase 2 Servicios Administrados

**Para:** Fausto Santana  
**Entorno:** solo `justech_dev` → https://erp.justech.do  
**Producción:** no usar  
**Objetivo:** Validar visualmente el flujo Contacto → Levantamiento → PDF → Oportunidad → Cotización → Servicio → Fee → Suscripción → Ticket  

**Usuarios DEMO UAT (solo DEV):**

| Usuario | Login | Password | Rol |
|---|---|---|---|
| Manager | `uat_ms_manager` | `JustechUAT!2026` | Administrador MS (+ Ventas/Helpdesk para navegar vínculos) |
| Comercial | `uat_ms_commercial` | `JustechUAT!2026` | Comercial MS |
| Técnico | `uat_ms_technician` | `JustechUAT!2026` | Técnico MS (sin write fees) |
| Sin permisos | `uat_ms_noperm` | `JustechUAT!2026` | Usuario interno sin grupo MS |

También puede usar `fausto@justech.do` si ya tiene acceso a DEV.

**Capturas de referencia:** `evidence/managed-services-phase2/manual-validation/`  
**Matriz técnica:** `manual-validation/uat_validation_matrix.json`

---

## Referencias rápidas

| Registro | URL |
|---|---|
| Resumen | https://erp.justech.do/odoo/action-1579 |
| Lista Servicios | https://erp.justech.do/odoo/action-1577 |
| **MS-2026-0001** | https://erp.justech.do/odoo/justech.managed.service/1 |
| **MS-2026-0002** | https://erp.justech.do/odoo/justech.managed.service/2 |
| **LEV-2026-0007** | https://erp.justech.do/web#id=7&model=justech.managed.service.assessment&view_type=form&view_id=6669 |
| Oportunidad 284 | https://erp.justech.do/odoo/crm.lead/284 |
| Cotización C-0003890 | https://erp.justech.do/odoo/sale.order/816 |
| Suscripción C-0003891 | https://erp.justech.do/odoo/sale.order/817 |
| Ticket 691 | https://erp.justech.do/odoo/helpdesk.ticket/691 |
| Contacto Credicefi | https://erp.justech.do/odoo/res.partner/1963 |
| PDF | `evidence/managed-services-phase2/LEV-2026-0007_Credicefi.pdf` |

---

## Checklist (marque Aprobado / Rechazado)

### 0. Menú

1. Abrir app **Servicios Administrados**.
2. Verificar menú: **Resumen · Servicios Administrados · Levantamientos · Fees / Igualas · Tickets**.
3. Confirmar que la entrada principal abre **Resumen** (kanban por estado), no solo Levantamientos.

| Resultado | ☐ Aprobado ☐ Rechazado |
| Observación | |

### 1. Resumen

1. Menú → **Resumen**.
2. Debe verse columna **Activo** con MS-2026-0001 y MS-2026-0002.
3. En MS-0001 debe verse fee RD$35,000 y tickets abiertos.

| Resultado | ☐ Aprobado ☐ Rechazado |
| Observación | |

### 2. MS-2026-0001 (flujo completo)

1. Abrir **MS-2026-0001**.
2. Verificar: Cliente Credicefi, Contacto DEMO, Estado **Activo**, Comercial/Técnico Fausto Santana.
3. Vínculos: LEV-2026-0007, Oportunidad, C-0003890, C-0003891, equipo Soporte Justech.
4. Pestaña **Fee y facturación**: RD$35,000, Mensual, producto Servicios de Iguala, auto-billing **desactivado**.
5. Pestaña **Alcance**: L1/L2/L3 marcados.
6. Smart buttons: Levantamientos(1), Oportunidad, Cotizaciones, Suscripción, Tickets(1), Cliente.
7. Abrir cada smart button y confirmar navegación correcta.
8. **Tickets** debe mostrar solo el ticket 691 de ese servicio.

| Resultado | ☐ Aprobado ☐ Rechazado |
| Observación | |

### 3. MS-2026-0002 (iguala histórica)

1. Abrir **MS-2026-0002**.
2. Confirmar **sin** Levantamiento, **sin** Oportunidad, **sin** Cotización.
3. Verificar fee RD$15,000, fechas inicio 2025-01-01 / renovación 2027-01-01.
4. Pestaña Alcance: horas 16, usuarios 20, equipos 25, servicios incluidos/excluidos.
5. Confirmar que se puede guardar sin exigir levantamiento (probar edición menor y Guardar).

| Resultado | ☐ Aprobado ☐ Rechazado |
| Observación | |

### 4. LEV-2026-0007 (botones / no duplicados)

1. Abrir levantamiento con URL de vista form (`view_id=6669`) o desde lista Levantamientos → abrir registro (no “Ver respuestas”).
2. Estado: **Servicio creado**.
3. Botones visibles: Descargar PDF, Vista previa PDF, Abrir oportunidad, Abrir cotización, Abrir Servicio Administrado.
4. **No** debe ofrecer Crear oportunidad / Crear Servicio (ya existen).
5. Pulsar Abrir oportunidad → mismo registro (id 284). Pulsar Abrir Servicio → MS-0001.
6. Pulsar Descargar PDF → descarga QWeb.

| Resultado | ☐ Aprobado ☐ Rechazado |
| Observación | |

### 5. Oportunidad / Cotización / Suscripción

1. Oportunidad **Ganado**, nombre Servicios Administrados — Credicefi, smart buttons Levantamientos + Servicio Adm.
2. Cotización **C-0003890** draft, vínculos a MS-0001 y LEV-0007 (sin líneas de precio forzadas).
3. Suscripción **C-0003891** draft, plan Mensual, `is_subscription`, producto Iguala RD$35,000 — **no confirmar ni facturar**.

| Resultado | ☐ Aprobado ☐ Rechazado |
| Observación | |

### 6. Ticket 691

1. Abrir ticket **DEMO F2 — Consulta soporte Credicefi**.
2. Verificar Cliente Credicefi, Servicio MS-2026-0001, Equipo Soporte Justech, estado Nuevo, prioridad Alta.
3. Desde MS-0001 → Tickets → solo ese ticket.

| Resultado | ☐ Aprobado ☐ Rechazado |
| Observación | |

### 7. Contacto Credicefi

1. Abrir contacto **Credicefi** (id 1963).
2. Smart buttons estándar Odoo (Oportunidades, Ventas, Tickets, Suscripciones…) pueden aparecer.
3. Abrir **Más** y verificar: Servicios Adm. (2), Levantamientos (2), Tickets MS, Cotiz. MS, Suscrip. MS.
4. No debe haber doble botón para el mismo concepto estándar (los MS están con sufijo MS / Adm.).

| Resultado | ☐ Aprobado ☐ Rechazado |
| Observación | |

### 8. Permisos

| Perfil | Qué probar | Esperado | Resultado |
|---|---|---|---|
| Manager | Abrir MS-0001, editar fee | Puede | ☐ OK ☐ KO |
| Comercial | Ver servicios, abrir levantamiento/cotización | Puede ver; fee page visible | ☐ OK ☐ KO |
| Técnico | Abrir MS-0001 alcance y tickets | Puede leer; **no** puede guardar cambio de fee | ☐ OK ☐ KO |
| Sin permisos | Abrir app Servicios Administrados | Sin acceso a modelos MS | ☐ OK ☐ KO |

### 9. No impacto

| Control | Esperado | Resultado |
|---|---|---|
| Correos reales enviados en este UAT | 0 | ☐ OK ☐ KO |
| Facturas generadas por suscripción DEMO | 0 (draft) | ☐ OK ☐ KO |
| Producción | No tocada | ☐ OK ☐ KO |

---

## Firma de validación

- Fecha: _______________
- Resultado global: ☐ Aprobado ☐ Aprobado con observaciones ☐ Rechazado
- Observaciones:

---

## Notas conocidas (no bloquean el flujo)

1. Smart buttons MS en Contacto pueden estar bajo **Más** por overflow de Odoo.
2. En MS-0001, smart button Cotizaciones puede contar 2 (cotización + suscripción vinculadas al servicio).
3. Toast “push notifications” del navegador/DEV es ajeno al módulo.
4. Cotización C-0003890 deliberadamente sin líneas de producto (precio se arma en Sales).
5. Suscripción permanece en borrador a propósito.
