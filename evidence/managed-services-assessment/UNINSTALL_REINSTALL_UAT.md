# UNINSTALL / REINSTALL UAT — justech_managed_services

**Entorno:** solo `justech_dev`  
**Producción:** **NO tocada** (`justech_managed_services` = `ABSENT` en BD `justech`).  
**Backup fresco usado:** `/opt/odoo-dev/backups/p0-ms-uat-manual-20260715_201527/`  
(contenido: `justech_dev.dump`, `filestore_justech_dev.tgz`, hashes SHA256, restore test PASS)

## Procedimiento ejecutado

1. Backup validado (antes del UAT manual).
2. Clear cola de módulos atascada en DEV (ajena): `base_industry_data`, `software_reseller` en `to upgrade` → restaurados a `installed` (solo DEV; requería desbloquear uninstall).
3. `button_immediate_uninstall()` sobre `justech_managed_services` → estado `uninstalled`; modelo fuera del registry.
4. `systemctl restart odoo-dev` → active; `/web/login` HTTP 200.
5. Smoke post-uninstall:
   - `res.partner` / `crm.lead` / `sale.order` / `account.move` → OK
   - Vistas combinadas partner/CRM/sale/account → OK y **sin** restos `justech_ms_assessment`
6. `button_immediate_install()` → `installed 19.0.1.0.0` (luego patch `19.0.1.0.1`)
7. `button_immediate_upgrade()` → OK
8. Smoke post-reinstall: modelos OK; vistas partner/CRM con smart button MS de nuevo.
9. Datos de prueba recreados (fixture Credicefi `LEV-2026-0002`) porque uninstall eliminó registros del modelo.

## Resultados

| Chequeo | Resultado |
|---|---|
| Odoo inicia tras uninstall | PASS |
| Contactos / CRM / Ventas / Facturación (modelos + vistas) | PASS |
| Sin errores de vistas heredadas residuales | PASS |
| Reinstall limpia | PASS |
| Upgrade | PASS |
| Smoke final | PASS |

## Rollback

Restaurar `/opt/odoo-dev/backups/p0-ms-uat-manual-20260715_201527/` (dump + filestore) y reiniciar `odoo-dev.service`.

## Nota

No se ejecutó restore completo al cierre: el ciclo uninstall/reinstall ya validó integridad; se dejó módulo instalado + fixture nuevo para continuidad en DEV.
