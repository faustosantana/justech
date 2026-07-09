# CLEANUP_PLAN — Data UAT-MENU- (NO ejecutar hasta aprobación)

**Prefijo:** `UAT-MENU-`  
**Backup pre-cambio:** ver `BACKUP_PATH.txt`

## Registros a eliminar

```sql
-- Partners, productos, facturas, pagos, extractos con prefijo UAT-MENU-
-- Ejecutar script inverso basado en UAT_CREATED_RECORDS.json
```

## Procedimiento recomendado

1. Restaurar desde backup si se requiere rollback total.
2. O ejecutar script de limpieza por IDs en `UAT_CREATED_RECORDS.json` (partners → payments → moves → statements).
3. Validar NCF consumidos durante UAT (documentar secuencias avanzadas).
4. Healthcheck post-limpieza HTTP 200.

## Rollback menús

Restaurar `hellenia_ui_pre.tar.gz` del backup y `-u hellenia_ui` si la navegación debe revertirse.
