# Administración Justech Enterprise — VALIDATION v2

**Fecha:** 2026-07-11  
**Host:** erp.justech.do (`vmi3364393`)  
**DB:** justech_dev  
**Rama:** feature/fiscal-standard-consolidation  
**Backup pre:** `/opt/odoo-dev/backups/jac-enterprise-pre-20260711_213310`

## Resultado

| Check | Resultado |
|------|-----------|
| Login HTTPS | 200 |
| Productos (6) | PASS |
| Catálogo dinámico | PASS (12 módulos) |
| Garantías → producto warranty | PASS |
| Activación por empresa | PASS |
| Motores 4/4 (JUSTECH electronic; resto NCF tradicional) | PASS |
| Desactivación / reactivación | PASS |
| Reauth hash PBKDF2 (env + secreto servidor) | PASS |
| Clave incorrecta | PASS (UserError) |
| Secretos no en auditoría | PASS |
| GL balanceado | PASS |
| justech_modules instalado (sesión/clave) | PASS |

## Secreto

- `JUSTECH_ADMIN_CENTER_PASSWORD_HASH` en systemd drop-in + `/opt/odoo-dev/secrets/justech_admin_center_password.hash`
- **No** está en Git. El propietario debe rotar la clave temporal de bootstrap.

## Rollback

1. Restaurar backup `jac-enterprise-pre-20260711_213310`
2. `git revert` del commit de esta entrega
3. `-u justech_admin_center` / reinstalar versión anterior
