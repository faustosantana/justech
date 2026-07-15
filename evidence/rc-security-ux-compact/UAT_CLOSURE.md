# P0 — Permisos Justech compactos (Producción)

**Fecha:** 2026-07-15  
**BD:** justech  
**Módulo:** justech_security_ux **19.0.3.1.1**  
**Entorno:** https://justgroup.app/odoo  

## Alcance

Solo UX / presentación (XML, JS, SCSS). Sin cambios a Python de sincronización, ACL, ir.rule, implied_ids.

## Backup

- Compact pre: `/root/backups/justech/p0-security-ux-compact-20260715_105509/`
- Closure: `/root/backups/justech/p0-security-ux-closure-20260715_133817/`

## UAT visual (navegador real)

Usuario revisado: Fausto Santana (id 5).

- Un módulo visible a la vez (chips)
- Buscador: aplicar pagos → Pagos; anular NCF → Fiscal; B13 → Compras
- Resumen general panel compacto
- Capacidades adicionales con etiquetas
- Contabilidad sin ruptura letra-a-letra
- Sin fondos blancos hardcoded en clases justech-jx
- Tema oscuro (variables Odoo): sin cuadros blancos justech
- Permisos Avanzados intactos + aviso técnico

Capturas: `screenshots/`

## Seguridad post-cleanup

Usuario temporal `uat_browser_compact` eliminado.

| Chequeo | Resultado |
|---|---|
| ACL same (antes/después delete UAT) | YES |
| Record Rules same | YES |
| implied_ids same | YES |
| res_groups_users_rel | solo cambio esperado por delete UAT |
| company_ids | solo cambio esperado por delete UAT |
| No-wipe SAVEPOINT uid=5 | PASS (delta 0) |

## Rollback

1. Restaurar `/root/backups/justech/p0-security-ux-compact-20260715_105509/module_before/`
2. `-u justech_security_ux` únicamente
3. Verificar fingerprint ACL/rules/implied
