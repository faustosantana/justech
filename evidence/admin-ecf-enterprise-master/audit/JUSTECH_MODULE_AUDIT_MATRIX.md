# Matriz de auditoría — módulos Justech (justech_dev)

Fecha: 2026-07-11 (UTC) · Entorno: erp.justech.do / justech_dev · Rama: feature/fiscal-standard-consolidation

## Inventario instalado (18 justech_*)

| Producto | Submódulo | Módulo técnico | Alcance | Administrar | Diagnosticar | Estado | Problema | Corrección | Riesgo |
|---|---|---|---|---|---|---|---|---|---|
| Core | Administración Justech | justech_admin_center | global | Consola | Health findings | PASS | — | UX 2.4.0 | bajo |
| Core | Seguridad y roles | justech_modules | global | detalle | health | PASS | — | — | bajo |
| Core | Multiempresa | justech_core | global | detalle | health | PASS | — | — | bajo |
| Fiscal | Padrón DGII | justech_l10n_do_base | global | Hub padrón | controles reales | PASS | antes activaba por empresa | scope global + hub | medio |
| Fiscal | Motor NCF | justech_l10n_do_ncf | company | rangos NCF | rangos/datos | PASS | — | — | alto |
| Fiscal | Reportes DGII | justech_l10n_do_reports | company | reportes | health | PASS | — | — | alto |
| Fiscal | Centro Fiscal | justech_fiscal_admin | company | Fiscal hub | hub | PASS | abría pantallas mezcladas | hub propio | medio |
| Fiscal | Salud Fiscal | justech_l10n_do_adel_freeze | company | Fiscal hub | health | PARCIAL | sin operación dedicada | MISS operation OK | bajo |
| Fiscal | Justech e-CF | justech_ecf_admin (+core/xml/signature/dgii/queue) | company | Hub e-CF | controles e-CF | PASS (mock) | nuevo | arquitectura 6 módulos | alto |
| Finanzas | Retenciones operativas | justech_l10n_do_payments_withholding | company | catálogo + wizard cobro | health | PASS | status vacío | cableado 623/wizard | medio |
| Finanzas | Tesorería | justech_l10n_do_treasury | company | Treasury hub | health | PASS | botones sin acción | ADMIN_ACTIONS + hub | medio |
| Garantías | Registro | justech_warranty | company | dashboard garantías | health | PASS | caía a form genérico | xmlids reales | medio |
| Auditoría | Auditoría global | justech_global_audit_log | global | dashboard auditoría | health | PASS | sin acciones | xmlids reales | bajo |
| Integraciones | (vacío) | — | — | empty state | — | PASS vacío | sin addons | — | bajo |

## Acciones ADMIN_ACTIONS validadas

- OK: 46
- MISS intencionales: `justech_fiscal_admin.operation`, `justech_l10n_do_adel_freeze.operation`

## Validación funcional e-CF (mock)

- XML generado + hash
- Envío mock → estado `accepted`, TrackID `MOCK-*`
- Producción DGII bloqueada por ValidationError (Gate)
- 15 XSD oficiales embebidos en `justech_ecf_xml/data/xsd`
- Auth center SHA256 intacto: `4f3896c25af52d5011e7d844a438d748172c92ada699818dc1c610ec7253b2d3`
- HASH password 64 bytes intacto
- GL: UNBALANCED_MOVES=0 · MOVES=2647

## No validado en navegador en este bloque (pendiente)

- Tour completo modo claro/oscuro de cada botón
- Firma real con P12 autorizado
- Llamadas a DGII certificación (sin credenciales)
- API OpenAPI completa / recepción automática de compras
- Benchmarks 1k–10k
