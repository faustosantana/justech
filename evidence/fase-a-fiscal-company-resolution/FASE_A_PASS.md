# Fase A — PASS real (seguridad + multiempresa Centro Fiscal)

**Fecha:** 2026-07-11  
**Entorno:** `erp.justech.do` / `justech_dev` (solo DEV)  
**Producción:** no tocada  
**Commit:** no realizado (según instrucción)

## Objetivo

Resolver empresa activa del Centro Fiscal vía `env.company` / `allowed_company_ids` (Odoo 19), sin company_id fija ni singleton del primer registro.

## Resultado

**FASE_A_PASS**

## Matriz empresas (shell + navegador)

| Empresa | res_id | NCF disp. (UI) | Issues (shell) | PASS |
|---------|--------|----------------|----------------|------|
| JUSTECH S.R.L. | 3 | 856 | 52 | Sí |
| PlugSafe SRL | 25 | 655 | 6 | Sí |
| Just Office SRL | 21 | 859 | 51 | Sí |
| Omni Solutions SRL | 26 | 859 | 6 | Sí |

Singletons: 1 por empresa. Sin duplicados.

## Navegador real (switcher + action-1502)

Flujo validado: cambiar empresa en switcher → abrir `action-1502` → centro correcto.

1. Switcher Just Office → Centro `/center/21`, datos Just Office (NCF 859, 1 error)
2. Switcher PlugSafe → action-1502 → `/center/25`, título PlugSafe, NCF **655**
3. Switcher Omni → action-1502 → `/center/26`, título Omni, NCF 859
4. Switcher JUSTECH → action-1502 → `/center/3`, título JUSTECH, NCF **856**, **5 errores** (detalle: Cliente sin RNC, Facturas sin NCF)

Sin AccessError / RPC_ERROR / OwlError en UI (solo ruido push notifications).

## Roles

| Rol | Abre Centro | Resultado |
|-----|-------------|-----------|
| System (`jinette@...`) | Sí | PASS |
| Admin Fiscal | Sí | PASS |
| Responsable Fiscal | No (AccessError) | PASS |
| Usuario Fiscal | No | PASS |
| Contador | No | PASS |
| Ventas | No | PASS |
| Compras | No | PASS |

Tipos fiscales legibles para Usuario Fiscal (01–17 con nombres).

## Feature flags

8 globales únicos: `ncf_motor`, `ncf_dual_write`, `provider_historical_only`, `dgii_reports`, `payments_withholding`, `duplicate_blocking`, `fiscal_dashboard`, `diagnostic_alerts`. Sin duplicados.

## GL

Posted lines balanceados por empresa (SQL): CID 1/2/3/4 → `bal=True`.

## Arquitectura confirmada

- Centro: un acceso admin; datos de empresa activa
- Tipos: globales
- Rangos/consumo/pagos/retenciones/errores: por empresa
- Salud: detalle por `center_id` de la empresa activa

## No avanzado

Fase B (padrón admin polish) — pendiente aprobación / PASS aceptado.
