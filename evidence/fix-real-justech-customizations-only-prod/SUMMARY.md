# fix-real-justech-customizations-only — PROD

**Fecha:** 2026-07-07  
**Ambiente:** hellenia_prod (https://odoo.hellenia.cloud)  
**Backup:** `fix-real-justech-customizations-only-2026-07-06_232948.dump`  
**Módulos:** justech_modules 19.0.1.8.0, justech_admin 19.0.2.11.0

## Resultado

| Check | Estado |
|-------|--------|
| Validación script | **PASS** |
| Healthcheck | **PASS** |

## Tarjetas visibles

**Usuario cliente:** 3 tarjetas  
1. Fiscal RD / NCF / DGII  
2. UX Fiscal / Contactos y Facturas  
3. Reportes y Documentos Corporativos  

**Usuario interno it@justech.do:** 4 tarjetas (+ Control Justech)

**POS Fiscal:** oculto *(hellenia_pos no instalado/validado en PROD)* — correcto.

## Eliminados

CRM, IA, RRHH, Marketplace, Manufactura, Nómina, Activos Fijos, Ventas, Compras, Inventario — **no aparecen**.

## Nota sobre causa raíz

La pantalla **Módulos del Cliente** ya filtraba correctamente vía backend; el catálogo completo (CRM, Ventas, etc.) seguía visible desde **Centro de Control → Módulos**, que usaba `get_commercial_catalog()`. Este fix redirige ese flujo a las personalizaciones reales y unifica la fuente de verdad en `REAL_JUSTECH_CUSTOMIZATIONS`.
