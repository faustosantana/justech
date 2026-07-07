# CLEAN-2B — Limpieza final de contactos

**Resultado:** PASS  
**Backup:** `/opt/odoo-projects/hellenia/backups/hellenia-prod/clean-2b-2026-07-07_171518`

## Antes
- Partners totales: 11
- Visibles (usuario normal): 8
- Visibles comerciales/prueba (no preservados): 5 (Demo 15 × 5)

## Eliminados
- Partners: 5 (Demo 15 normal, accounting, sales, purchase, inventory)
- Usuarios demo inactivos: 5 (`usuario.*.demo14/demo15`)

## Preservados (6)
| Partner | Motivo |
|---------|--------|
| Hellenia, S.R.L. | `res.company` |
| Administrator | `base.partner_admin` + usuario `admin` |
| JustechIT | `res.users(active): it@justech.do` |
| OdooBot | usuario sistema `__system__` |
| Public user | usuario sistema `public` |
| Portal User Template | usuario sistema `portaltemplate` |

## Después
- Clientes: 0
- Proveedores: 0
- Contactos comerciales (rank): 0
- Visibles no preservados: 0
- Licencia Hellenia: activa (id=4, PRO)
- Healthcheck: PASS

## Nota licencia
La licencia comercial no estaba persistida en BD al iniciar CLEAN-2B. Se recreó con catálogo LICENSE-4 (5 módulos) y commit explícito post-limpieza.
