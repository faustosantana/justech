# fix-real-justech-customizations-only — TEST

**Fecha:** 2026-07-07  
**Ambiente:** hellenia_test (https://test.hellenia.cloud)  
**Módulos:** justech_modules 19.0.1.8.0, justech_admin 19.0.2.11.0

## Resultado

| Check | Estado |
|-------|--------|
| Validación script | **PASS** |
| Tests Odoo | **61/61 PASS** |
| Healthcheck | **PASS** |

## Tarjetas visibles

**Usuario cliente (view_only):** 4 tarjetas  
1. Fiscal RD / NCF / DGII  
2. UX Fiscal / Contactos y Facturas  
3. Reportes y Documentos Corporativos  
4. POS Fiscal *(hellenia_pos instalado y configurado en TEST)*

**Usuario interno it@justech.do:** 5 tarjetas (+ Control Justech)

## Eliminados

CRM, IA, RRHH, Marketplace, Manufactura, Nómina, Activos Fijos, Ventas, Compras, Inventario — **no aparecen**.

## Fuente de verdad

Catálogo explícito `REAL_JUSTECH_CUSTOMIZATIONS` — no se generan tarjetas desde módulos Odoo instalados ni desde `justech.commercial.product` completo.
