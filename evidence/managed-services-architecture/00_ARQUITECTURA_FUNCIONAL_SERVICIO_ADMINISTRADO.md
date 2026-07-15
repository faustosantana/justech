# Arquitectura funcional definitiva — Servicios Administrados Justech

**Módulo:** `justech_managed_services` (evolución del mismo módulo; no se crea módulo nuevo)  
**Entorno de trabajo futuro:** únicamente `justech_dev` (`erp.justech.do`)  
**Producción:** fuera de alcance hasta aprobación y despliegue controlado  
**Estado de este documento:** **PROPUESTA PARA APROBACIÓN** — sin implementación  
**Fecha:** 2026-07-15  
**Versión del documento:** 1.0  
**Ancla de partida:** Fase 1 aprobada — *Levantamiento* (`justech.managed.service.assessment`, v19.0.1.0.2)

---

## 0. Declaración de alcance y principios

### Qué se aprueba con este documento

La visión, el modelo de datos, las integraciones Odoo, el menú, los smart buttons, el flujo de vida y el plan de fases. **No se escribe código** hasta que el propietario apruebe expresamente esta arquitectura.

### Principios no negociables

1. **El registro principal es el Servicio Administrado**, no el levantamiento.
2. **Un solo módulo** (`justech_managed_services`) evoluciona; no se crea otro addon paralelo.
3. **No duplicar Odoo estándar:** CRM, Contactos, Ventas, Suscripciones, Helpdesk, Proyecto, Partes de horas, Contabilidad y Documentos se reutilizan por herencia / relación.
4. **El levantamiento permanece** como primer paso del ciclo y como smart button dentro del Servicio.
5. **Fase 1 no se rompe:** el modelo `justech.managed.service.assessment` se reutiliza y se cuelga del nuevo maestro; el formulario público y token se conservan.
6. Todo cambio futuro: auditable, reversible, documentado; desarrollo solo en `justech_dev`.

### Situación actual (Fase 1 — congelada como aprobada)

| Elemento | Hoy |
|---|---|
| Modelo maestro implícito | Levantamiento (`justech.managed.service.assessment`) |
| Menú raíz | Servicios Administrados → Levantamientos |
| Integraciones | `res.partner`, `crm.lead`, mail, website/portal |
| Smart buttons | Contadores de levantamientos en Contacto y CRM |
| Fuera de alcance ya declarado | Contratos, igualas, fees, helpdesk, SLA operativo, facturación recurrente |

---

## 1. Modelo de datos (cómo debe quedar)

### 1.1 Diagrama conceptual

```text
res.partner (Cliente)
    │
    ├── 1..N  justech.managed.service          ← MAESTRO (Servicio Administrado)
    │            │
    │            ├── 1..N  justech.managed.service.assessment   (Levantamientos — YA EXISTE)
    │            ├── 0..N  crm.lead / sale.order (vínculos)
    │            ├── 0..1  sale.order (cotización ganadora) / sale.subscription (iguala)
    │            ├── 0..N  helpdesk.ticket
    │            ├── 0..N  justech.ms.asset / covered user / visit / hour pool (operación)
    │            ├── 0..N  account.move (facturas relacionadas)
    │            └── 0..N  documentos / reportes mensuales
    │
    └── smart buttons agregados hacia todo lo anterior
```

### 1.2 Relación cardinal sugerida

| Relación | Cardinalidad | Regla |
|---|---|---|
| Cliente → Servicios Administrados | 1 → N | Un cliente puede tener varias igualas (sedes, contratos, niveles). |
| Servicio → Levantamientos | 1 → N | Histórico; el más reciente “vigente” se marca como primario opcional. |
| Servicio → Oportunidad CRM | N → 0..1 | Preferible 1 oportunidad comercial por servicio en etapa pre-contrato. |
| Servicio → Cotización / Suscripción | 1 → 0..1 (activa) + historial | La iguala operativa vive en Sales/Subscription; el Servicio la apunta. |
| Servicio → Tickets | 1 → N | Helpdesk con `managed_service_id`. |
| Servicio → Activos / Usuarios cubiertos | 1 → N | Inventario operativo del alcance contractual. |

### 1.3 Separación de responsabilidades

| Capa | Qué guarda | Dónde |
|---|---|---|
| Comercial | Pipeline, probabilidad, propuesta | CRM + Ventas |
| Contractual / recurrente | Fee, ciclo, renovación | Suscripciones / Órdenes + vínculo al Servicio |
| Operativa | SLA, tickets, horas, visitas, activos | Helpdesk + campos/modelos satélite del Servicio |
| Descubrimiento | Cuestionario tecnológico | Levantamiento (Fase 1) |
| Financiera | Facturas, cobros | Contabilidad (account.move) |
| Maestro de negocio Justech | Estado de vida del servicio, KPIs, alcance | **`justech.managed.service`** |

El **Servicio Administrado** es el hub operativo-comercial de Justech. No sustituye a Sales ni a Helpdesk; los orquesta.

---

## 2. Modelos nuevos que existirán

Solo modelos Justech cuando no haya equivalente estándar sano. Nombres provisionales (sujetos a ajuste al implementar).

### 2.1 Modelo maestro (obligatorio)

#### `justech.managed.service` — Servicio Administrado

Ficha principal. Campos mínimos de negocio:

| Grupo | Campos |
|---|---|
| Identidad | `name` (secuencia tipo `SA-2026-0001`), `title`, `partner_id`, `company_id` |
| Equipo | `consultant_id`, `salesperson_id`, `team_id` (opcional) |
| Ciclo de vida | `state` (ver § Estados), `date_start`, `date_renewal`, `date_end` |
| Comercial | `opportunity_id`, `assessment_ids`, `primary_assessment_id` |
| Contractual | `sale_order_id` / `subscription_id`, `contract_ref`, `fee_monthly`, `currency_id` |
| Alcance | `service_level`, `included_services` (HTML/tags), `excluded_services` |
| Capacidad | `users_covered`, `devices_covered`, `hours_included`, `hours_consumed` (compute), `visits_included`, `visits_done` (compute) |
| SLA | `sla_policy_id` (si Helpdesk SLA) o política Justech |
| Operación | contadores smart button hacia tickets, activos, facturas, horas, visitas |
| Comunicación | `mail.thread`, `mail.activity.mixin` |

### 2.2 Modelos satélite recomendados (módulo mismo)

| Modelo propuesto | Propósito | ¿Evitable con estándar? |
|---|---|---|
| `justech.ms.asset` | Equipo / activo cubierto por la iguala | Parcialmente con `maintenance.equipment` o productos lotificados; Justech suele necesitar campos de cobertura contractual → **sí, modelo liviano o herencia** |
| `justech.ms.covered.user` | Usuario final cubierto | Contactos hijos + flag; o modelo thin con M2O partner |
| `justech.ms.visit` | Visita presencial programada/realizada | Puede ser `project.task` o actividad calendar; si el negocio exige cuotas contractuales, modelo thin o tareas tipadas |
| `justech.ms.hour.ledger` (opcional) | Bolsa / consumo de horas de iguala | Preferible `account.analytic.line` (timesheet) con vínculo; ledger solo si hace falta “bolsa contractual” explícita |
| `justech.ms.monthly.report` | Informe mensual al cliente | Puede ser `documents.document` + plantilla; modelo thin para ciclo/estado de entrega |
| `justech.ms.sla.policy` (opcional) | Catálogo Justech de niveles | Preferible reutilizar Helpdesk SLA si está instalado |

### 2.3 Lo que NO se modela como nuevo

| Concepto | Reutilizar |
|---|---|
| Prospecto / oportunidad | `crm.lead` |
| Cotización / orden | `sale.order` |
| Iguala / fee recurrente | `sale.subscription` (Enterprise) **o** orden recurrente / módulo fee existente si ya opera en Justgroup — **decision gate en Fase 2.0** |
| Ticket | `helpdesk.ticket` |
| Horas | `account.analytic.line` / timesheet |
| Proyecto de implementación | `project.project` / `project.task` |
| Factura | `account.move` |
| Documento contractual | `documents.document` o adjuntos |

### 2.4 Evolución del modelo Fase 1

`justech.managed.service.assessment` **se conserva**.

Cambios conceptuales (cuando se implemente):

- Nuevo M2O obligatorio/recomendado: `managed_service_id` → `justech.managed.service`.
- El estado del levantamiento sigue siendo el del formulario (draft/sent/…); el estado de negocio del cliente vive en el Servicio.
- Crear levantamiento desde Servicio (o CRM) asigna automáticamente el maestro.
- Migración: levantamientos existentes en DEV/PROD (cuando toque) se asocian a un Servicio generado por partner (regla: 1 servicio “legado” por partner con assessment sin servicio).

---

## 3. Modelos estándar de Odoo a reutilizar

| App Odoo | Modelo | Uso en el ciclo |
|---|---|---|
| Contacts | `res.partner` | Cliente centro; smart buttons |
| CRM | `crm.lead` | Prospecto → oportunidad; vínculo al Servicio |
| Sales | `sale.order` | Propuesta económica / cotización |
| Subscriptions* | `sale.subscription` | Contrato/iguala y fee mensual recurrente |
| Helpdesk* | `helpdesk.ticket`, SLA | Tickets operativos bajo el Servicio |
| Project* | `project.project`, `project.task` | Implementación post-contrato |
| Timesheets* | `account.analytic.line` | Horas consumidas |
| Accounting | `account.move` | Facturación de la iguala y extras |
| Documents* | `documents.document` | Contratos firmados, actas, reportes |
| Mail | chatter / activities | Seguimiento humano |
| Website/Portal | (ya en Fase 1) | Formulario de levantamiento; portal futuro opcional |

\*Dependencias Enterprise: confirmar licenciamiento en el stack Justgroup antes de hard-depend. Estrategia: **dependencias opcionales** (`sale`, `helpdesk`, etc. según fase) para no bloquear el maestro.

### Dependencias del módulo (evolución prevista)

```text
Fase 1 (actual):  base, mail, contacts, crm, website, portal
Fase 2+:          + sale_management (mínimo)
Fase 3+:          + sale_subscription | (alternativa fee Justech)
Fase 4+:          + helpdesk (+ sla)
Fase 5+:          + project, hr_timesheet (o analytic)
Opcional:         documents
```

---

## 4. Smart Buttons

### 4.1 En `res.partner` (Cliente)

| Botón | Destino |
|---|---|
| Servicios Administrados | `justech.managed.service` |
| Levantamientos | assessments (existente) |
| Propuestas / Cotizaciones | `sale.order` filtradas (origen MS / linked) |
| Contratos / Suscripciones | subscription u órdenes contractuales |
| Tickets | `helpdesk.ticket` |
| Activos | `justech.ms.asset` |
| Usuarios cubiertos | covered users |
| Facturas | `account.move` |
| Horas | analytic / timesheet |
| SLA / Incumplimientos | vista filtrada helpdesk SLA (si aplica) |

### 4.2 En `justech.managed.service` (ficha maestra)

| Botón | Destino |
|---|---|
| Levantamientos | assessments del servicio |
| Oportunidad | `opportunity_id` |
| Cotizaciones | sale orders ligadas |
| Contrato / Suscripción | subscription / SO |
| Tickets | helpdesk |
| Activos | assets |
| Usuarios | covered users |
| Visitas | visits / tasks |
| Horas | timesheets / ledger |
| Facturas | account.move |
| Reportes mensuales | monthly reports / documents |
| Documentos | documents / attachments |

### 4.3 En `crm.lead`

Mantener Levantamientos; agregar **Servicio Administrado** (crear/vincular).

### 4.4 En `sale.order` / Subscription / Helpdesk ticket

Botón inverso al Servicio Administrado (Many2one `managed_service_id` por herencia).

---

## 5. Menú del módulo (rediseño)

```text
Servicios Administrados                    (aplicación)
├── Dashboard
├── Servicios                              → justech.managed.service (acción principal)
├── Levantamientos                         → assessment (Fase 1, secundario)
├── Propuestas                             → sale.order (contexto MS)
├── Contratos / Igualas                    → subscriptions / contractual SO
├── Clientes Administrados                 → res.partner (filtro: con servicio)
├── Operación
│   ├── Tickets
│   ├── SLA
│   ├── Visitas
│   ├── Horas
│   └── Activos
│   └── Usuarios Cubiertos
├── Facturación                            → facturas relacionadas MS
├── Reportes
│   ├── Reportes mensuales
│   └── Análisis / pivots
└── Configuración
    ├── Niveles de servicio
    ├── Políticas SLA (si propias)
    ├── Tipos de visita
    ├── Plantillas de alcance
    └── Ajustes
```

**Cambio clave:** el menú raíz ya no abre solo Levantamientos; abre **Dashboard** o **Servicios**.

### Dashboard (MVP funcional)

KPIs sugeridos (sin over-engineering inicial):

- Servicios por estado (kanban/aggregate)
- Levantamientos pendientes de revisión
- Propuestas en negociación
- Renovaciones próximos 30/60/90 días
- Tickets abiertos / fuera de SLA
- Horas consumidas vs incluidas (servicios activos)
- Fee mensual recurrente (pipeline activo)

---

## 6. Flujo completo: Prospecto → Renovación

```text
[1] Prospecto (CRM)
        ↓  crear / vincular
[2] Servicio Administrado (state = Prospecto)
        ↓  enviar enlace
[3] Levantamiento (Fase 1) → recibido
        ↓
[4] Evaluación técnica (actividades + resumen en Servicio)
        ↓
[5] Propuesta técnica (documento / sección del Servicio)
        ↓
[6] Propuesta económica / Cotización (sale.order)
        ↓
[7] Negociación (CRM + revisiones SO)
        ↓
[8] Aprobado (won + state Servicio)
        ↓
[9] Contrato / Iguala (subscription o SO contractual + documentos)
        ↓
[10] Implementación (project)
        ↓
[11] Servicio Activo
        ↓ ciclo continuo
[12] Tickets + SLA + Horas + Visitas
        ↓
[13] Fee mensual → Facturación
        ↓
[14] Reportes mensuales
        ↓
[15] Renovación (nueva cotización / extensión subscription)
        → Activo | Suspendido | Finalizado
```

### Mapeo flujo → estados del Servicio

Ver sección de estados (§ abajo en punto 1 ampliado / tabla §Estados).

### Rol del levantamiento en el flujo

- Es **puerta de entrada de datos**, no el expediente del cliente.
- Puede haber re-levantamientos anuales o por ampliación de alcance.
- Un Servicio Activo puede abrir un nuevo assessment sin crear un segundo servicio, salvo cambio contractual mayor (entonces sí nuevo Servicio o enmienda).

---

## 7. Integración CRM, Helpdesk, Ventas, Suscripciones y Facturación

### 7.1 CRM

| Momento | Comportamiento propuesto |
|---|---|
| Lead/oportunidad de “Servicios Administrados” | Acción: Crear Servicio (+ opcional Levantamiento) |
| Servicio.prospecto | `opportunity_id` obligatorio en etapas pre-aprobación (configurable) |
| Oportunidad ganada | Impulsa estado Servicio → Aprobado (manual confirmado o asistido) |
| UTM / source | Conservar origen “Levantamiento…” de Fase 1 |

No inventar un CRM paralelo dentro del módulo.

### 7.2 Ventas (Propuesta económica / Cotización)

- Heredar `sale.order` con `managed_service_id`.
- Productos de catálogo: iguala mensual, horas extras, visitas extras, onboarding.
- La “propuesta técnica” puede vivir como:
  - PDF/documento adjunto al Servicio, y/o
  - descripción enriquecida en la SO,
  - sin modelo “propuesta” duplicado si Sales cubre lo económico.

### 7.3 Suscripciones / Iguala / Fee

**Decision gate crítico (aprobar en este documento o en kickoff Fase 2):**

| Opción | Pros | Contras |
|---|---|---|
| **A. `sale.subscription`** | Estándar Odoo, renovación, facturación recurrente | Requiere Enterprise + capacitación |
| **B. Reutilizar fee recurrente Justech** (si existe en el stack productivo) | Ya alineado a operación local | Acoplar módulos; evitar doble fuente de verdad |
| **C. Solo `sale.order` + facturación manual/cron liviano** | Simple al inicio | Débil para renovaciones a escala |

**Recomendación:** Opción **A** como estándar arquitectónico; si el stack Justgroup ya factura igualas con otro mecanismo, **integrar** ese mecanismo al Servicio (M2O) en lugar de crear un cuarto motor de fees.

### 7.4 Helpdesk + SLA

- Heredar ticket: `managed_service_id`, posiblemente `partner_id` forzado desde el Servicio.
- Equipo Helpdesk “Servicios Administrados”.
- SLA Odoo (si disponible) mapeado al `service_level` del Servicio.
- Tickets sin Servicio quedan permitidos (otros negocios Justech) pero el Dashboard MS solo cuenta los vinculados.

### 7.5 Facturación

- Las facturas las genera Sales/Subscription/Accounting como hoy.
- El Servicio muestra smart button y KPIs (`invoice_ids` via SO/subscription).
- No crear motor de facturación propio.

### 7.6 Project + Timesheets

- Al pasar a **Implementación**: crear proyecto plantilla vinculado.
- Horas de iguala: timesheets analíticos con cuenta analítica del Servicio o del contrato.
- Visitas: tareas o modelo thin contabilizando contra `visits_included`.

---

## 8. Procesos automáticos (propuestos)

| Automatismo | Trigger | Efecto |
|---|---|---|
| Secuencia SA-… | create Servicio | Nombre único |
| Crear Levantamiento desde Servicio | botón | assessment con partner + managed_service_id + token |
| Al completar Levantamiento | assessment → done | Actividad al consultor; sugerir state Servicio → Levantamiento recibido |
| Al vincular cotización | SO confirm interest | State → Propuesta enviada (opcional, asistido) |
| Al marcar oportunidad Won | wizard | State → Aprobado + checklist contrato |
| Al activar suscripción/contrato | confirmed | State → Contrato firmado / Implementación |
| Al cerrar proyecto implementación | done | State → Activo; fecha inicio/renovación |
| Cron renovación | diario | Actividades 90/60/30 días antes de `date_renewal` |
| Cron suspensión | impago / regla negocio | Proponer Suspendido (no auto-suspender sin regla clara) |
| Cómputo horas/visitas | write timesheet/visit | Actualizar consumos en ficha |
| SLA breach | helpdesk | Actividad / color kanban en Servicio |
| Reporte mensual | cron fin de mes | Borrador de reporte + actividad |

Los cambios de estado **comercialmente sensibles** (Aprobado, Contrato firmado, Activo, Suspendido) deben ser **asistidos** (botón + validaciones), no “magia silenciosa”.

---

## 9. Procesos manuales (propuestos)

| Proceso | Quién | Por qué manual |
|---|---|---|
| Crear prospecto / calificar | Comercial | Juicio humano |
| Enviar enlace de levantamiento | Consultor | Control de timing y correo |
| Evaluación técnica y propuesta técnica | Consultor | Expertise |
| Armar cotización y descuentos | Comercial | Negociación |
| Aprobar precio / margen | Gerencia (si aplica) | Gobernanza |
| Firma de contrato / iguala | Legal/Comercial | Compliance |
| Kickoff implementación | PM/Consultor | Coordinación cliente |
| Visitas especiales fuera de cuota | Operaciones | Autorización |
| Horas extras facturables | Operaciones + Comercial | Evitar fuga de margen |
| Suspender / finalizar servicio | Admin MS | Impacto contractual |
| Contenido del reporte mensual | Consultor | Valor percibido |
| Renegociar renovación | Comercial | Relación cliente |

---

## 10. Fases de desarrollo recomendadas

> Ninguna fase se inicia sin aprobación explícita. Esta sección es **roadmap**, no orden de ejecución inmediata.

### Fase 1 — Levantamiento *(COMPLETA Y APROBADA)*

Formulario público, token, PDF, CRM/Contactos, permisos. **Congelar comportamiento**; solo mantenimiento correctivo si surge bug crítico.

### Fase 2 — Maestro Servicio Administrado + rediseño de menú *(siguiente tras aprobar arquitectura)*

- Modelo `justech.managed.service` + estados + ficha.
- Relación assessment → service; migración de datos DEV.
- Menú: Dashboard MVP + Servicios + Levantamientos.
- Smart buttons en partner y servicio.
- Sin Helpdesk/Subscriptions aún (enlaces preparados).
- Criterio de salida: Credicefi (u otro) se opera desde ficha Servicio; levantamiento es botón.

### Fase 3 — Comercial (Propuesta / Cotización / Negociación)

- Dependencia `sale`.
- Herencia SO + flujos CRM ↔ Servicio.
- Transiciones de estado hasta Aprobado.
- Criterio: cotizar iguala desde el Servicio sin Excel paralelo.

### Fase 4 — Contrato / Iguala / Fee / Facturación

- Decision gate Subscription vs fee Justech.
- Fechas inicio/renovación, fee mensual en ficha.
- Smart buttons de facturas.
- Criterio: un servicio activo muestra fee y última factura.

### Fase 5 — Operación (Tickets, SLA, Horas, Visitas)

- Helpdesk + SLA + timesheets + visitas.
- Consumos vs incluidos en ficha.
- Criterio: ticket de iguala nace vinculado al Servicio.

### Fase 6 — Activos, Usuarios cubiertos, Reportes, Renovación

- Inventario de cobertura.
- Reportes mensuales.
- Automatismos de renovación.
- Criterio: el módulo es el centro diario de operaciones de igualas.

### Fase 7 — Portal cliente / autoservicio (opcional)

- Ver tickets, reportes, consumo de horas (sin exponer backoffice).

---

## 11. Riesgos

| # | Riesgo | Impacto | Mitigación |
|---|---|---|---|
| R1 | Convertir el Servicio en un “ERP dentro del ERP” duplicando Sales/Helpdesk | Alto | Strict boundary: orquestar, no reemplazar |
| R2 | Romper Fase 1 (token/formulario) al renombrar conceptos | Alto | Mantener assessment intacto; solo M2O nuevo |
| R3 | Dependencias Enterprise no disponibles (subscription/helpdesk) | Alto | Feature flags / dependencias por fase |
| R4 | Doble fuente de verdad del fee mensual | Alto | Un solo motor de recurrencia; Servicio solo referencia |
| R5 | Estados del Servicio vs estados del assessment vs CRM confunden usuarios | Medio | Matriz de estados documentada + formación |
| R6 | Migración de levantamientos huérfanos | Medio | Script DEV primero; 1 Servicio legado por partner |
| R7 | Sobrecargar Fase 2 con operación completa | Alto | Cumplir freeze: Fase 2 = maestro + menú + vínculo |
| R8 | Permisos multi-equipo (comercial vs operaciones) | Medio | Record rules por consultor/salesperson/equipo |
| R9 | Contadores smart button costosos en performance | Medio | stored counts / read_group; no computes pesados en listados |
| R10 | Scope creep de activos estilo CMDB | Medio | Activos “cubiertos por iguala”, no ITAM completo |
| R11 | Producción tocada por error | Crítico | Solo justech_dev; checklist despliegue |
| R12 | Reportes PDF con mojibake (ya residual DEV) | Bajo | Seguir en backlog técnico aparte |

---

## 12. Recomendaciones para convertirlo en el centro operativo de igualas

1. **Renombrar mentalmente el producto:** de “app de levantamientos” a “app de Servicios Administrados”; el levantamiento queda como onboarding.
2. **Una ficha, una verdad operativa:** comercial y operaciones miran el mismo `justech.managed.service`.
3. **Kanban del Servicio por estado de vida** como tablero diario (no solo lista de forms).
4. **Catálogo de productos de iguala** en Sales (SKU claros: nivel, usuarios, horas, visitas).
5. **Decision gate temprano** sobre Subscriptions vs fee existente — evita reescritura cara en Fase 4.
6. **Plantillas:** project de implementación, checklist post-levantamiento, plantilla de reporte mensual.
7. **Gobernanza de estados:** botones con restricciones (no editar `state` libre en form salvo Admin).
8. **Métricas de negocio desde el día 1 de Fase 2:** # servicios activos, MRR (fee), churn, renovaciones — aunque MRR se complete en Fase 4.
9. **No mezclar** soporte break/fix de hardware externo o proyectos one-shot con igualas sin discriminador; el Servicio es para managed services.
10. **Capacitación comercial + operaciones** antes de go-live de cada fase.
11. **Conservar evidencia y rollback** por fase en `/evidence/managed-services-architecture/`.
12. **Criterio de éxito final:** un consultor abre el cliente → Servicio Activo → ve contrato, fee, tickets, horas, próxima renovación **sin salir a hojas de cálculo**.

---

## Estados del Servicio Administrado (detalle)

| Estado | Código sugerido | Significado | Entrada típica | Salida típica |
|---|---|---|---|---|
| Prospecto | `prospect` | Interés; aún sin datos completos | Crear desde CRM/partner | Enviar levantamiento |
| Levantamiento recibido | `assessment_received` | Formulario completado | Assessment done | Evaluación |
| En evaluación | `evaluation` | Análisis técnico interno | Manual / actividad | Propuesta preparada |
| Propuesta preparada | `proposal_ready` | Técnica (+/- económica borrador) | Manual | Envío propuesta |
| Propuesta enviada | `proposal_sent` | En manos del cliente | SO enviada / mail | Negociación / Aprobado |
| Negociación | `negotiation` | Cambios de alcance/precio | Manual | Aprobado / perdido |
| Aprobado | `approved` | Cliente aceptó | Won / botón | Contrato |
| Contrato firmado | `contracted` | Iguala legalizada | Subscription/docs | Implementación |
| Implementación | `implementation` | Onboarding | Proyecto abierto | Activo |
| Activo | `active` | Operación recurrente | Cierre implementación | Suspendido / Renovación / Finalizado |
| Suspendido | `suspended` | Pausa (impago/cliente) | Manual gobernado | Activo / Finalizado |
| Finalizado | `closed` | Fin de relación | Manual | — |

**Nota:** “Perdido” puede ser `cancel`/`lost` adicional o cierre de la oportunidad CRM sin ensuciar el maestro; recomendación: estado `lost` o archivar Servicio en Finalizado con motivo.

Los estados propios del **levantamiento** (draft/sent/in_progress/done/…) **no se eliminan**; conviven un nivel abajo.

---

## Matriz “qué es Justech vs qué es Odoo”

| Necesidad de negocio | Dueño de la verdad |
|---|---|
| ¿Este cliente tiene iguala managed? | `justech.managed.service` |
| ¿Quién es el prospecto y probabilidad? | `crm.lead` |
| ¿Qué precio y líneas se ofrecieron? | `sale.order` |
| ¿Qué se factura cada mes? | Subscription / Accounting |
| ¿Qué ticket está abierto? | `helpdesk.ticket` |
| ¿Qué dijo el cliente del entorno TI? | `justech.managed.service.assessment` |
| ¿Cuántas horas quedan este mes? | Timesheet + campos del Servicio |
| ¿Cuál es el estado comercial-operativo global? | **Estado del Servicio** |

---

## Impacto sobre datos y UX existentes (Fase 1)

| Tema | Decisión propuesta |
|---|---|
| Formulario público | Sin cambio de URL ni token strategy en Fase 2 |
| Menú | Levantamientos baja un nivel; sigue accesible |
| Permisos | Reutilizar grupos `group_ms_user` / `group_ms_manager`; ampliar ACL al maestro |
| DEMO / LEV-2026-* en DEV | Migrar a Servicios al implementar Fase 2 |
| Documentación FUNCIONAL.md | Reescribir en Fase 2 kickoff (no ahora en código) |

---

## Decisiones que el propietario debe confirmar

Antes de iniciar Fase 2, se solicita aprobación explícita de:

1. **Modelo maestro** `justech.managed.service` como centro.
2. **Lista de estados** (tabla anterior).
3. **Decision gate de fee:** Subscription vs mecanismo Justech existente vs diferir a Fase 4.
4. **Alcance estricto de Fase 2:** solo maestro + menú/dashboard MVP + vínculo levantamientos + smart buttons básicos (sin tickets/fees aún).
5. **No crear módulo nuevo**; evolución de `justech_managed_services`.
6. Trabajo solo en `justech_dev`; sin merge a main; sin Producción.

---

## Criterio de aceptación de *esta* arquitectura (no del software)

Esta propuesta se considera **aprobada** cuando el propietario confirme por escrito (chat/correo) algo equivalente a:

> “Apruebo la arquitectura funcional del Servicio Administrado como maestro y autorizo iniciar el diseño/implementación de la Fase 2 en justech_dev según el alcance de la sección 10.”

Hasta entonces: **no código, no upgrade de módulo, no cambios de menú en el servidor.**

---

## Anexos

### A. Entregables de evidencia de esta propuesta

- Este archivo: `evidence/managed-services-architecture/00_ARQUITECTURA_FUNCIONAL_SERVICIO_ADMINISTRADO.md`

### B. Referencia Fase 1

- Módulo: `custom/justech_managed_services/`
- Docs actuales: `docs/FUNCIONAL.md`, `docs/TECNICO.md`
- Modelo: `justech.managed.service.assessment`

### C. Fuera de esta propuesta

- Implementación de pantallas, XML, Python, data migration scripts.
- Cambios en Producción.
- Merge a `main`.
- Envío de correos reales.
- Rediseño del formulario público de 16 secciones (permanece válido).

---

*Fin del documento — espera de aprobación para iniciar Fase 2.*
