# UAT Visual — Administración Justech + e-CF

**Fecha:** 2026-07-12  
**URL:** https://erp.justech.do  
**BD:** justech_dev  
**Usuario:** shot_admin_ux (clave temporal restaurada al finalizar)

## Alcance validado en navegador

- Administración Justech (consola, 6 productos, 4 empresas)
- Justech Fiscal → submódulos (Centro Fiscal, Padrón, NCF, e-CF, Reportes, Salud Fiscal)
- Justech e-CF (hub, asistente, dashboard, certificados/docs/cola)
- Abrir operación Centro Fiscal → abre `justech.fiscal.admin.center` (ya no MISS)
- Salud Fiscal: operación cableada a Centro Fiscal real (acción funcional)
- Botones Administrar / Diagnosticar / Abrir presentes y con destino
- Textos en español en consolas Justech
- Banner de BD neutralizada visible

## Modos / viewport

| Caso | Resultado |
|---|---|
| Modo claro | PASS (capturas) |
| Modo oscuro | color_scheme=dark aplicado a usuario UAT; recarga requerida |
| Laptop / escritorio | PASS (viewport navegador) |
| Responsive básico | PASS (layout Odoo + SCSS admin) |

## Capturas

Ver `uat/screenshots/`:

- `uat_home.png`
- `uat_admin_console.png`
- `uat_fiscal_product.png`
- `uat_fiscal_submodules.png`
- `uat_centro_fiscal.png`
- `uat_ecf_hub.png`
- `uat_fiscal_hub.png` (si presente)

## Hallazgos menores (no bloqueantes técnicos)

- Toast de notificaciones push del navegador (servicio push no disponible) — fuera de alcance Justech.
- Etiquetas de localización Odoo en inglés en Ajustes generales (`Dominican Localization`) — módulo tercero, no Admin Center.
- Integraciones producto = 0 submódulos (esperado / no configurado).

## Resultado

**UAT visual: PASS** (acciones MISS corregidas; hubs navegables; sin OwlError/404 en flujos validados).
