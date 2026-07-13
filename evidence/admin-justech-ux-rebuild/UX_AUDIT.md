# UX Audit — Administración Justech (RECHAZADA)

**Fecha:** 2026-07-12  
**Entorno:** `erp.justech.do` / `justech_dev`  
**Rama:** `feature/fiscal-standard-consolidation`  
**HEAD:** `fdc43e0`  
**Veredicto:** Interfaz actual **NO** lista para cliente Enterprise.

## 1. Problemas críticos observados

| # | Problema | Causa raíz | Impacto |
|---|----------|------------|---------|
| 1 | HTML crudo visible | Campos `Html` sin `widget="html"` + HTML embebido en kanban | Rompe confianza; ilegible |
| 2 | Estados contradictorios | `Atención` por hallazgos info / `Activo` por instalado ≠ empresa | Decisiones erróneas |
| 3 | Pendientes con controles OK | Dominio de pendientes sin filtrar severidad real | Ruido operativo |
| 4 | Textos concatenados (`…Global`) | Label+valor en spans sin `display:block` | Parece bug de datos |
| 5 | Usuarios UAT en consola | Página notebook en dashboard principal | Contamina producto |
| 6 | Breadcrumbs rotos | Stack Odoo + HTML inventado + sin `clear_breadcrumbs` | Pérdida de orientación |
| 7 | Dashboard sobrecargado | KPIs + HTML + productos + pendientes + UAT | No cabe en 30s |
| 8 | Garantías deformada | Capacidades fake en HTML + métricas sin filtro | Producto no administrable |
| 9 | Pestañas/botones duplicados | Header + 7 tabs con las mismas acciones | Capacitación innecesaria |
| 10 | Globales tratados como empresa | Padrón/checks sin distinción UX | Activaciones falsas |

## 2. Pantallas auditadas (objetivo → fallo)

### Dashboard principal
- **Objetivo:** Elegir empresa y ver qué requiere acción.
- **Falla:** Contadores duplicados, HTML, UAT, pendientes inflados, productos mezclados.

### Vista por empresa / company hub
- **Objetivo:** Operar una empresa.
- **Falla:** Misma sobrecarga HTML; estados inconsistentes.

### Producto (Fiscal / Finanzas / Garantías / Core)
- **Objetivo:** Capacidades + acción.
- **Falla:** HTML shells, tabs de más, “Activo” con 0 empresas, capacidades fake en Garantías.

### Centro de pendientes
- **Objetivo:** Solo problemas reales.
- **Falla:** Incluye info/OK residuales; acciones a veces genéricas.

### Estado del sistema
- **Objetivo:** Controles por categoría.
- **Falla:** Nombres técnicos (Registry Odoo); mezclado con pendientes.

## 3. Taxonomía de estado (única, a implementar)

| Estado | Significado |
|--------|-------------|
| Correcto | Operativo sin acción pendiente real |
| Atención | Acción pendiente no bloqueante |
| Error | Bloquea o compromete operación |
| No configurado | Disponible pero no configurado para la empresa |
| Inactivo | Deshabilitado funcionalmente |
| No aplica | Fuera del alcance de la empresa |

Reglas:
- No contar `severity=info` como pendiente.
- No marcar Atención por producto opcional no usado.
- “Activo” solo si hay activación por empresa (o alcance global instalado).

## 4. Arquitectura de navegación (3 niveles)

```
Administración Justech → Empresa → Producto → Capacidad → Acción
```

Acciones canónicas: Configurar | Abrir operación | Ver estado | Resolver.

## 5. Plan de reconstrucción (solo presentación + lógica de estado)

1. Sustituir shells HTML por campos nativos + vistas.
2. Unificar motor de estado (empresa / producto / capacidad).
3. Pendientes = warning/error/critical únicamente.
4. Quitar UAT del dashboard; acción técnica solo `group_system`.
5. Breadcrumbs con `clear_breadcrumbs` + Volver real.
6. Producto: encabezado + 4 KPIs + grid capacidades + actividad.
7. Garantías: sin HTML; capacidades 3.1–3.6 como tarjetas nativas si inactivo → CTA único.
8. Globales: badge “Servicio global”, sin activar/desactivar por empresa.

## 6. Archivos de presentación a reescribir

- `models/justech_admin_console.py` (KPIs/estado, no auth)
- `models/justech_admin_product.py` (shell/estado)
- `models/justech_admin_module.py` (estado/cobertura)
- `models/justech_admin_company_hub.py`
- `models/justech_admin_system_status.py`
- `models/justech_admin_health_finding.py` / health service filtros
- Views console/product/module/health/status
- `static/src/scss/admin_center.scss`
- e-CF hub presentation only

## 7. No tocar

Auth/hash, motores fiscales, datos, GL, NCF, padrón datos, pagos, conciliaciones.

## 8. Evidencia de backup

Backup previo a reconstrucción: ver log de sesión `admin-justech-ux-rebuild-*` en `/opt/odoo-dev/backups/`.
