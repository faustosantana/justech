# PR-1.5 — Nav cleanup + auditoría UX

**Fecha:** 2026-06-10  
**Depende de:** PR-1.4 (redirects admin)  
**Objetivo:** reducir ruido visual, ocultar placeholders, consolidar navegación admin.

---

## Cambios implementados

### 1. Placeholders ocultos del sidebar

**Archivos:** `frontend/src/lib/modules/types.ts`, `registry.ts`, `module-dashboard-page.tsx`

- Añadido `contentKey` tipado en `ModuleSection`.
- Nueva función `isSectionNavVisible()` — oculta secciones con `contentKey: "placeholder"` o `navHidden: true`.
- `moduleToNav()` filtra antes de construir `JAIOS_APPS[].nav`.
- `filterModuleQuickActions()` elimina accesos rápidos que apuntan a secciones ocultas.

**Hotfix PR-1.5.1 (2026-06-10):** misma regla extendida a dashboards:

- `filterModuleDashboardData()` — filtra KPIs, actividad reciente y alertas.
- `buildVisibleSectionActivity()` — fallback de actividad solo con secciones visibles.
- `isModuleHrefNavVisible()` — sanitiza cualquier enlace `/apps/{mod}/{sec}`.
- Estado vacío: «No hay actividad reciente disponible para este módulo.»
- Sección «Acciones rápidas» oculta cuando no hay acciones válidas.

**Secciones ocultas:** 21 placeholders en:

| Módulo | Secciones ocultas |
|--------|-------------------|
| Compras | solicitudes, cotizaciones, órdenes, recepciones, aprobaciones |
| Inventario | categorías, almacenes, movimientos, transferencias, ajustes |
| Facturación | cuentas-pagar, pagos, notas-credito |
| Proveedores | categorías, órdenes, historial, evaluaciones |
| Reportes | compras, personalizados |
| Agentes IA | logs |

Las rutas `/apps/{modulo}/{seccion}` siguen existiendo (deep links, bookmarks) pero muestran «en construcción» si se accede directamente.

### 2. Label tenant

| Ubicación | Antes | Después |
|-----------|-------|---------|
| `configuracion/empresas/page.tsx` | Empresas | **Empresa activa (tenant)** |
| `admin-sidebar.tsx` | Empresas | **Empresa activa (tenant)** |
| `registry.ts` (módulo configuracion) | Empresas | **Empresa activa (tenant)** |

### 3. Navegación admin simplificada

Eliminados del sidebar admin los atajos duplicados a integraciones individuales (M365, Odoo, WhatsApp, DGCP). El hub `/configuracion/integraciones` concentra el acceso.

Renombrado «Usuarios y roles» → **Usuarios** (la página de roles permanece separada en `/configuracion/roles`).

### 4. Código muerto eliminado

- `frontend/src/components/layout/sidebar.tsx` — sidebar legacy no referenciado.
- `frontend/src/components/admin/admin-nav.tsx` — nav horizontal legacy sin imports.

---

## QA manual sugerido

1. Login admin → abrir **Compras** → sidebar muestra solo: Dashboard, Proveedores, Contratos, Reportes, Configuración (sin 5 placeholders).
2. Repetir con **Inventario** y **Proveedores**.
3. Dashboard de Compras → accesos rápidos no incluyen secciones ocultas; actividad reciente **no** enlaza Solicitudes/Recepciones/Órdenes (placeholders).
4. Dashboard **Inventario** → actividad vacía o sin links a categorías/almacenes/movimientos; KPIs sin href a placeholders.
5. Dashboard **Proveedores** → actividad y KPIs solo a Directorio/Listas (no categorías/órdenes/historial).
6. **Configuración → Empresa activa (tenant)** — label correcto.
7. Admin sidebar → sin entradas M365/Odoo/WhatsApp/DGCP sueltas; acceso vía Integraciones.

---

## Auditoría UX — duplicados y «mangú con arroz y mango»

Hallazgos para **Fase 2** (consolidación de producto, no bloqueante para Fase 1):

### A. Pantallas duplicadas / mismo contenido

| # | Problema | Ubicaciones | Propuesta |
|---|----------|-------------|-----------|
| UX-01 | **Certificaciones = Pendientes** | Empresas del Grupo: ambas usan `documentos:pendientes` | Fusionar en una sola sección «Pendientes y certificaciones» |
| UX-02 | **Calendario M365 × 4** | Calendario: mi-calendario, equipo, reuniones, eventos → todos `m365:operativo` | Una entrada «Calendario» + tabs internos en M365Workspace |
| UX-03 | **Tareas × 5 idénticas** | mis-tareas, equipo, vencidas, hoy, calendario → `tasks:list` | Una «Tareas» con filtros (mías/equipo/vencidas/hoy) en el componente |
| UX-04 | **Precios: buscador = productos = comparaciones = histórico** | 4 nav items, mismo `prices:search` | Sidebar: Resumen + Buscador + Listas + Alertas; el resto como tabs |
| UX-05 | **Hermes en 3 sitios** | Agentes IA (centro-hermes), Config IA (/configuracion/ia/hermes), Integraciones Hermes | Un solo centro Hermes bajo Agentes IA; config técnica bajo Integraciones |
| UX-06 | **Empresas del grupo × 3** | Launcher «Empresas del Grupo», Documentos→clientes, Config→empresa activa | Fase 2: un módulo «Entidades» con scope (grupo / tenant / cliente) |

### B. Módulos con baja densidad funcional

| Módulo | Secciones visibles post-cleanup | Riesgo UX |
|--------|--------------------------------|-----------|
| **Compras** | 4 (+ dashboard) | Mucho espacio para poco contenido Odoo-only |
| **Inventario** | 3 (+ dashboard) | Considerar ocultar del launcher hasta Odoo stock |
| **Facturación** | 5 | Aceptable (Odoo facturas) |
| **Clientes** | 8 | Solapamiento fuerte con CRM |

**Propuesta Fase 2:** flag `launcherVisible: false` en módulos &lt; N secciones operativas; merge CRM + Clientes.

### C. Pasos innecesarios

| # | Flujo | Problema | Propuesta |
|---|-------|----------|-----------|
| UX-07 | Config → General → card Integraciones → hub → M365 | 3 clics | Atajo directo en General para integraciones críticas (Odoo, M365) |
| UX-08 | Apps module config embed → link «Panel administración» | Salto a `/configuracion` genérico | Deep link al `configKey` correspondiente |
| UX-09 | Usuarios + Roles + Módulos + Reglas + Deptos | 5 páginas admin relacionadas | Wizard «Onboarding usuario» (usuario → rol → módulos → reglas) |

### D. Información repetida

| Área | Repetición |
|------|------------|
| Reportes | Cada módulo tiene «Reportes» → `reportes:centro` genérico |
| Configuración | Cada módulo tiene «Configuración» → distintos `config:*` pero misma UX embed |
| Integraciones admin | Hub + páginas dedicadas M365/Odoo/WhatsApp/DGCP (sidebar ya consolidado; URLs directas siguen válidas) |

---

## Qué NO se tocó (Fase 1)

- Launcher count (17 apps) — merge 17→10 es Fase 2.
- Registry app IDs.
- Rutas deep link de placeholders (solo ocultas en nav).
- Odoo, DGCP, M365 funcional.

---

## Rollback

1. Revertir `isSectionNavVisible` / `moduleToNav` filter en `registry.ts`.
2. Restaurar `admin-sidebar.tsx` atajos integración desde git.
3. Restaurar labels «Empresas».
