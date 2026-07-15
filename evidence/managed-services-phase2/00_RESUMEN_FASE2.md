# Fase 2 operativa — Servicios Administrados Justech

**Fecha:** 2026-07-15  
**Entorno:** `justech_dev` / `erp.justech.do`  
**Producción:** no tocada (`justech_managed_services` = ABSENT)  
**Rama:** `feature/managed-services-phase2`  
**Versión módulo:** `19.0.2.0.0`  
**Backup:** `/opt/odoo-dev/backups/p2-managed-services-20260715_202722/justech_dev.dump` (51 MB)

---

## 1. Arquitectura aplicada

El registro maestro es `justech.managed.service` (Servicio Administrado / Iguala).  
El levantamiento Fase 1 permanece y se vincula con `managed_service_id`.

Flujo operativo implementado:

```
Contacto → Levantamiento → PDF → Aprobar → Oportunidad CRM
→ Cotización (sale.order) → (Opp ganada) → Servicio Administrado
→ Fee registrado → Suscripción estándar (sale.order is_subscription)
→ Ticket Helpdesk
```

**Mecanismo de recurrencia elegido:** `sale_subscription` (pedido `sale.order` con `is_subscription` + `plan_id`).  
No se creó motor de facturación paralelo.  
`justech_recurring_fee` existe en DEV (0 fees previos) pero no se hard-depende; se enlaza la suscripción estándar.

---

## 2. Modelos

### Nuevos
| Modelo | Descripción |
|---|---|
| `justech.managed.service` | Maestro iguala / servicio administrado |

### Evolucionados
| Modelo | Cambio |
|---|---|
| `justech.managed.service.assessment` | Estados comerciales, `managed_service_id`, cotizaciones, botones, PDF |

### Heredados
| Modelo | Campos / acciones |
|---|---|
| `res.partner` | Smart buttons MS |
| `crm.lead` | `justech_managed_service_id`, smart buttons, crear cotización |
| `sale.order` | `justech_managed_service_id`, `justech_assessment_id` |
| `helpdesk.ticket` | `justech_managed_service_id` |

---

## 3. Menú

Servicios Administrados → Resumen | Servicios Administrados | Levantamientos | Fees / Igualas | Tickets

---

## 4. ACL / grupos

- Administrador de Servicios Administrados  
- Comercial de Servicios Administrados  
- Usuario de Servicios Administrados  
- Técnico de Servicios Administrados (lectura servicios/levantamientos; sin write fees)

Record rules por asignación + multi-compañía.

---

## 5. Resultados UAT (DEMO justech_dev)

| Paso | Resultado |
|---|---|
| Contacto | Credicefi (id 1963) |
| Levantamiento | **LEV-2026-0007** (id 7) |
| PDF | `evidence/managed-services-phase2/LEV-2026-0007_Credicefi.pdf` (37 KB) |
| Oportunidad | **Servicios Administrados — Credicefi** (crm.lead id 284) |
| Cotización | **C-0003890** (draft, sin líneas de precio forzadas) |
| Opp ganada | stage is_won |
| Servicio | **MS-2026-0001** → estado **Activo** |
| Fee | DOP 35,000 mensual; producto `Servicios de Iguala`; `auto_billing=False` |
| Suscripción | **C-0003891** (draft, `is_subscription`, no confirmada, **0 facturas nuevas**) |
| Ticket | id **691** — DEMO F2 — Consulta soporte Credicefi |
| Iguala histórica | **MS-2026-0002** (sin levantamiento) |
| Correos | **0** en el levantamiento |
| NCF / e-CF | módulos siguen installed; no se modificó código fiscal |
| Producción | **ABSENT** |

Navegación verificada: levantamiento↔oportunidad↔cotización↔servicio↔ticket↔suscripción.

---

## 6. Smoke facturación / ventas

- Cotización y suscripción quedaron en **draft**.  
- Facturas generadas por este UAT: **0**.  
- No se tocó NCF, e-CF, ni confirmación de facturas.

---

## 7. Pendientes reales (siguiente fase)

1. Automatización de facturación recurrente (solo cuando se apruebe).  
2. Consumo de horas / visitas vs incluidas.  
3. Reportes mensuales al cliente.  
4. Penalidades / motor SLA avanzado (reutilizar Helpdesk SLA).  
5. Productos DEMO dedicados (catálogo) — hoy se reutiliza `Servicios de Iguala` existente.  
6. Vista Configuración (menú omitido a propósito por no vacío).  
7. Portal cliente.  
8. Hardening UI comercial (kanban resumen KPIs más ricos).

---

## 8. Rollback

1. Restaurar `/opt/odoo-dev/backups/p2-managed-services-20260715_202722/justech_dev.dump`  
2. Revertir / checkout código a `19.0.1.0.2`  
3. `-u justech_managed_services` o reinstalar versión previa  

Producción no requiere rollback (no desplegado).

---

## 9. Confirmaciones

- Trabajo solo en `justech_dev`.  
- Sin merge a `main`.  
- Sin despliegue a Producción.  
- Sin correos reales.  
- Sin facturas reales confirmadas.
