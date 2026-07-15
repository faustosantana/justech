# RC-SECURITY-UX-FINAL — Evidencia DEV

**Entorno:** erp.justech.do · BD `justech_dev` · Módulo `justech_security_ux` 19.0.3.0.0  
**Backup:** `/root/backups/justech_dev/rc-security-ux-final-20260715_045203/`  
**Producción:** no modificada.

## Inventario

- `baseline.txt` — users/groups/acl/rules/rel
- `groups_inventory.tsv` — xmlids relevantes
- `implied_ids.tsv` — implicaciones
- `justech_installed.txt` — módulos instalados

## UAT

- `uat_shell.log` — casos 1–9 + integridad (54 PASS, 0 FAIL) con SAVEPOINT
- `dev_uninstall_shell.log` — caso 10 desinstalación (grupos/ACL/rules/usuarios intactos)
- `dev_before_uninstall.txt` / `dev_after_reinstall.txt` — invariantes post-reinstalación

## Aplicar pagos (caso 5)

| Ítem | Valor real |
|---|---|
| Grupo | `account.group_account_invoice` |
| Puede | facturar; registrar cobros; registrar pagos; aplicar pagos (ACL create payment PASS) |
| Segregación fina cobro/pago/aplicar | **No existe** en esta instancia |
| Banco aparte | `account.group_validate_bank_account` |
| Advertencia UI | obligatoria en sección Pagos y Bancos |

## Hellenia

Referencias funcionales/código en el módulo: **0** (solo mención en README/CHANGELOG de “sin dependencias”).

## Rollback

1. Restaurar `justech_security_ux.before.tgz` en addons DEV.  
2. `-u justech_security_ux` en `justech_dev`.  
3. Si hace falta: `pg_restore` desde `justech_dev.dump`.
