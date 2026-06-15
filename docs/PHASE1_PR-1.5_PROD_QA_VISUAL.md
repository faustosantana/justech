# PR-1.5 — QA visual en producción

**Entorno:** https://jaios.justech.do  
**Tenant:** justech  
**Fecha:** 2026-06-16  
**Deploy:** frontend reiniciado; cambios PR-1.5 activos en prod.

> **Nota histórica (2026-06-16):** Esta validación usó usuarios QA temporales (`qa-ventas@`, `qa-licitaciones@`, `qa-gerencia@`) **eliminados** tras auditoría. Ver [`QA_FICTITIOUS_USERS_REMOVAL.md`](QA_FICTITIOUS_USERS_REMOVAL.md). Política vigente: [`QA_DATA_POLICY.md`](QA_DATA_POLICY.md).

---

## Veredicto

| Área | Resultado |
|------|-----------|
| Launcher por rol | **PASS** (API + UI admin/usuario) |
| Configuración / Empresa activa | **PASS** |
| Sidebar placeholders ocultos | **PASS** |
| Accesos rápidos dashboard | **PASS** (botones) |
| Actividad reciente dashboard | **PASS** (hotfix PR-1.5.1) |
| Smoke funcional módulos clave | **PASS** |
| Hallazgos UX duplicados | **Documentados** — deuda Fase 2 |

**PR-1.5 APROBADO** — WARN actividad reciente resuelto con hotfix (`filterModuleDashboardData`, `buildVisibleSectionActivity`).

---

## 1. Launcher — apps por rol

Validado vía `GET /users/me/platform-access` + UI en prod (2026-06-16).

| Rol | Usuario | Apps visibles | Config en header | Config en grid |
|-----|---------|---------------|------------------|----------------|
| **Admin** | admin@justech.do | **17** | Sí (icono + footer) | Sí |
| **Gerencia** | *(cuenta QA eliminada — histórico)* | **17** | Sí | Sí |
| **Ventas** | *(cuenta QA eliminada — histórico)* | **16** | No | No |
| **Licitaciones** | *(cuenta QA eliminada — histórico)* | **10** | No | No |
| **Usuario** | marieli@justech.do | **16** | No | No |

### Lista exacta por rol

**Admin / Gerencia (17):**  
Comunicaciones, Empresas del Grupo, CRM, Ventas, Compras, Inventario, Facturación, Documentos, Licitaciones, Precios, Clientes, Proveedores, Tareas, Calendario, Reportes, Agentes IA, **Configuración**

**Ventas / Usuario (16):** igual sin Configuración

**Licitaciones (10):**  
Comunicaciones, Empresas del Grupo, Documentos, Licitaciones, Precios, Proveedores, Tareas, Calendario, Reportes, Agentes IA  
(sin CRM, Ventas, Compras, Inventario, Facturación, Clientes, Configuración)

Fuente API: `docs/qa-screenshots/pr15/api-launcher-report.json`

### Evidencia UI

- Admin: launcher completo con icono Configuración en header — capturado en sesión browser.
- Usuario: 16 tiles, sin Configuración ni link «Configuración del sistema» — **PASS**.
- Ventas / Licitaciones / Gerencia: listas confirmadas por API; UI ventas login verificado en sesión.

---

## 2. Configuración

| Check | Resultado | Evidencia |
|-------|-----------|-----------|
| Ya no dice solo «Empresas» en admin | **PASS** | Sidebar: **«Empresa activa (tenant)»** |
| Título página empresas | **PASS** | H2: **«Empresa activa (tenant)»** |
| Usuario sin permiso | **PASS** | `/configuracion` → redirect **`/dashboard`** (URL verificada) |
| Admin sidebar sin atajos M365/Odoo/WhatsApp/DGCP | **PASS** | 15 ítems (antes 19) |

**Admin sidebar actual (15):** General, Apariencia, Empresa activa (tenant), Usuarios, Roles y permisos, Módulos, Reglas, Departamentos, Integraciones, Integraciones de Proveedores, APIs/Conectores, Repositorios, Seguridad, Logs/Auditoría, Estado del sistema.

---

## 3. Sidebar — antes / después

> **Nota:** No hay captura prod pre-PR-1.5. «Antes» reconstruido desde registry pre-1.5 (placeholders visibles). «Después» medido en prod 2026-06-16.

| Módulo | Nav ANTES | Nav DESPUÉS | Placeholders ocultos |
|--------|-----------|-------------|----------------------|
| **Compras** | 10 | **5** | Solicitudes, Cotiz. proveedores, Órdenes, Recepciones, Aprobaciones |
| **Inventario** | 9 | **5** | Categorías, Almacenes, Movimientos, Transferencias, Ajustes |
| **Proveedores** | 9 | **5** | Categorías, Órdenes, Historial, Evaluaciones |
| **Reportes** | 9 | **7** | Compras, Personalizados |
| **Agentes IA** | 10 | **9** | Logs |

### Compras DESPUÉS (prod)

Sidebar visible: Dashboard, Proveedores, Contratos, Reportes, Configuración.  
**No aparecen** Solicitudes, Cotiz. proveedores, Órdenes de compra, Recepciones, Aprobaciones.

Deep link `/apps/compras/solicitudes` sigue mostrando «Solicitudes — en construcción» (esperado: ruta existe, nav oculta).

---

## 4. Dashboard — accesos rápidos

| Módulo | Acciones rápidas visibles | ¿Apuntan a placeholder? |
|--------|---------------------------|-------------------------|
| Compras | Proveedores, Comparar precios | **No** |
| Inventario | Productos, Consultar existencia | **No** |
| Ventas | (Odoo funcional) | **No** |
| Precios | Buscar producto, Listas, Comparar | **No** |

### Actividad reciente — RESUELTO (hotfix PR-1.5.1)

**Antes:** En Compras (y otros módulos sin datos API), «Actividad reciente» listaba placeholders (Solicitudes, Recepciones…) con «Abrir sección».

**Después (hotfix):**
- `buildVisibleSectionActivity()` — solo secciones con `isSectionNavVisible()`.
- `filterModuleDashboardData()` — sanitiza KPIs, alertas y actividad con `isModuleHrefNavVisible()`.
- Compras muestra: Proveedores, Contratos, Reportes, Configuración (sin placeholders).
- Inventario / módulos Odoo sin actividad API: mensaje «No hay actividad reciente disponible para este módulo.»

**Archivos:** `registry.ts`, `dashboard-data.ts`, `module-dashboard-page.tsx`, `module-dashboard.tsx`.

---

## 5. Hallazgos UX (captura + análisis)

### UX-A — Certificaciones vs Pendientes

| | |
|---|---|
| **a) Qué ve hoy** | Empresas del Grupo → **Pendientes** y **Certificaciones** son dos ítems de sidebar distintos. Ambas pantallas muestran **la misma lista** (Firma autorizada, Sello gomígrafo, Logo corporativo… por empresa, estado resolved). |
| **b) Por qué es redundante** | Mismo `contentKey: documentos:pendientes` en registry. El usuario no distingue qué cambia entre tabs. |
| **c) Consolidación** | Un solo ítem «Pendientes y certificaciones» con filtros (tipo doc / vencimiento). |

### UX-B — Calendario

| | |
|---|---|
| **a) Qué ve hoy** | 6 ítems sidebar: Mi calendario, Equipo, Reuniones, Recordatorios, Eventos, Config. Todos abren **M365Workspace** (Correo/Calendario/Teams/OneDrive). |
| **b) Redundancia** | Cuatro entradas distintas → mismo componente. Dashboard repite los mismos links en «Actividad reciente». |
| **c) Consolidación** | Una entrada «Calendario M365» + tabs internos (Mi / Equipo / Reuniones). |

### UX-C — Tareas

| | |
|---|---|
| **a) Qué ve hoy** | 8 ítems: Mis tareas, Equipo, Vencidas, Hoy, Calendario, Proyectos, Reportes, Config. Varios usan `tasks:list`. |
| **b) Redundancia** | Misma vista con distinto label; confunde qué filtro aplica. |
| **c) Consolidación** | Una «Tareas» con chips: Mías / Equipo / Vencidas / Hoy / Calendario. |

### UX-D — Precios

| | |
|---|---|
| **a) Qué ve hoy** | Resumen, Buscador, Productos, Listas, Por proveedor, Comparaciones, Histórico, Alertas, Reportes, Config. Buscador/Productos/Comparaciones/Histórico → mismo `prices:search`. |
| **b) Redundancia** | 4 entradas de nav → misma pantalla de búsqueda. |
| **c) Consolidación** | Resumen + Buscador (tabs: productos/comparar/histórico) + Listas + Alertas. |

### UX-E — Hermes

| | |
|---|---|
| **a) Qué ve hoy** | Agentes IA: Centro Hermes, Herramientas, Fuentes, Prompts. Además `/configuracion/ia/hermes` y integración Hermes en Config. |
| **b) Redundancia** | Tres rutas admin + dos rutas operativas al mismo concepto. |
| **c) Consolidación** | Centro Hermes único en Agentes IA; config técnica solo bajo Integraciones. |

### UX-F — Empresas del Grupo

| | |
|---|---|
| **a) Qué ve hoy** | Launcher «Empresas del Grupo», Documentos→«Empresas del grupo», Config→«Empresa activa (tenant)». |
| **b) Redundancia** | Tres conceptos de «empresa» sin jerarquía clara (grupo vs tenant vs cliente). |
| **c) Consolidación** | Módulo «Entidades» con scope: grupo / tenant / cliente. |

### UX-G — Documentos

| | |
|---|---|
| **a) Qué ve hoy** | 11 ítems sidebar incl. Repositorio, Empresas del grupo, Certificaciones, Búsqueda avanzada. Certificaciones duplica pendientes de empresas-grupo. |
| **b) Redundancia** | Solapamiento con Empresas del Grupo y Licitaciones (docs). |
| **c) Consolidación** | Documentos = repositorio transversal; empresas/licitaciones solo deep links contextuales. |

---

## 6. Navegación duplicada (≥3 rutas = deuda UX)

| Contenido | Rutas de acceso (≥3) | Deuda |
|-----------|----------------------|-------|
| **Hermes / IA config** | Agentes IA → Centro Hermes; Agentes IA → Prompts; Config → IA/Hermes; Config → Integraciones Hermes; Header Assistant | **Sí — 5 rutas** |
| **Microsoft 365** | Calendario app (6 subitems); Config → Integraciones → M365; `/m365/cuentas`; Quick action «M365 Operativo» | **Sí — 4 rutas** |
| **Empresas grupo** | Launcher; Documentos→Empresas del grupo; Empresas-grupo app; KPI dashboard Documentos | **Sí — 4 rutas** |
| **Configuración admin** | Header icon; Footer link; Launcher tile; `/configuracion` directo | **Sí — 4 rutas** (aceptable post-PR-1.4) |
| **Licitaciones DGCP** | Launcher; Licitaciones app; Documentos→Licitaciones; Agentes IA KPIs | **Sí — 4 rutas** |
| **Placeholders compras** | Deep link URL; Actividad reciente dashboard; (sidebar oculto) | **Sí — 3 rutas** (WARN PR-1.5) |

---

## 7. Métrica final

| Métrica | Antes PR-1.5 | Después PR-1.5 |
|---------|--------------|----------------|
| **Ítems sidebar Compras** | 10 | **5** |
| **Ítems sidebar Inventario** | 9 | **5** |
| **Ítems sidebar Proveedores** | 9 | **5** |
| **Ítems admin sidebar Config** | 19 | **15** |
| **Placeholders visibles en nav (total)** | ~21 | **0** |
| **Pantallas accesibles (URLs)** | Sin cambio | Sin cambio (deep links OK) |
| **Label «Empresas» en config admin** | Sí | **No** → «Empresa activa (tenant)» |
| **Duplicidades eliminadas** | — | Atajos M365/Odoo/WhatsApp/DGCP en admin sidebar; 21 placeholders fuera de nav |
| **Duplicidades pendientes** | — | Certificaciones/Pendientes; Calendario×6; Tareas×8; Precios×4; Hermes×5; Actividad reciente→placeholders |

---

## 8. Verificación funcional (smoke manual prod)

| Módulo | Ruta | Resultado | Notas |
|--------|------|-----------|-------|
| Empresas del Grupo | `/apps/empresas-grupo` | **PASS** | 4 perfiles, KPIs, pendientes cargan |
| Documentos | `/apps/documentos` | **PASS** | Repositorio, KPIs 67 pendientes |
| Licitaciones | `/apps/licitaciones/procesos` | **PASS** | 97 oportunidades, sync DGCP visible |
| M365 | `/apps/calendario/mi-calendario` | **PASS** | Bandeja correo M365 operativa |
| Hermes | `/apps/agentes-ia` | **PASS** | KPIs, Centro Hermes en nav |
| Configuración | `/configuracion/empresas` | **PASS** | Guard admin, label tenant correcto |

**Nada roto** por el cleanup de nav. Deep links a placeholders siguen funcionando (muestran «en construcción»).

---

## 9. Acciones pendientes antes de aprobar PR-1.5

1. **Decisión producto:** ¿Hotfix actividad reciente (filtrar placeholders) o aceptar como deuda Fase 2?
2. **Opcional:** Capturas PNG archivadas en repo (Playwright en container Alpine falla por libc; usar browser manual o CI con imagen Ubuntu).
3. **No abrir PR** hasta sign-off explícito del usuario sobre WARN + deuda UX.

---

## Referencias

- Implementación: `docs/PHASE1_PR-1.5_NAV_CLEANUP.md`
- API launcher: `docs/qa-screenshots/pr15/api-launcher-report.json`
- Script QA (eliminado): ~~`backend/scripts/qa_pr15_visual_prod.py`~~
