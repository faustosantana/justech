# PLAN_DE_ROLLBACK — Justech Fiscal v1.0

## Cuándo revertir

Revertir de inmediato si, durante o justo después del despliegue a Producción:

- Upgrade de módulo falla o deja la BD inconsistente.
- Usuarios no pueden facturar / asignar NCF.
- Padrón DGII vacío o integridad roja sin recuperación.
- Errores masivos RPC/Owl/Access en flujos ventas/compras.
- Backup pre-despliegue no es restaurable (no continuar; restaurar desde backup anterior conocido).

## Cómo revertir

1. **Detener** workers Odoo PROD (mantenimiento).
2. **Restaurar BD** desde el dump pre-despliegue (`pg_restore` / procedimiento oficial).
3. **Restaurar filestore** desde el tar pre-despliegue.
4. **Restaurar código** addons a la revisión git previa (tag/commit pre-release).
5. **Arrancar** Odoo y validar login.
6. **Smoke:** abrir factura draft, ver rango NCF, Centro Fiscal, un pago reciente.
7. **Comunicar** a Contabilidad: ventana extendida / reintento.

## Tiempo estimado

| Escenario | Tiempo |
|-----------|--------|
| Solo código (revert git + restart) | 15–25 min |
| BD + filestore completo | 45–90 min |
| Validación post-rollback | 15–20 min |

## Validaciones posteriores

- [ ] Login Admin + Contador
- [ ] `res_company` count esperado
- [ ] Padrón count > 0 y status green
- [ ] Rangos NCF activos
- [ ] Última factura posted intacta (nombre/NCF)
- [ ] Sin cola mail crítica nueva
- [ ] Informe de incidente en `/evidence/`

## Notas

- Nunca mezclar filestore de DEV con PROD.
- Documentar hash del commit revertido y ruta exacta del backup usado.
