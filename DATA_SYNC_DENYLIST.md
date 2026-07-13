# DATA SYNC DENYLIST — modelos técnicos prohibidos

**Nunca** sincronizar desde Producción hacia DEV (ni viceversa) los modelos /
tablas de esta lista. Son configuración, código declarado en BD, seguridad o
runtime.

## Prohibición explícita

### Framework Odoo (`ir_*` y afines)
- `ir.module.module` / `ir.module.module.dependency`
- `ir.model` / `ir.model.fields` / `ir.model.fields.selection`
- `ir.model.data` (XML IDs)
- `ir.ui.view` / `ir.ui.menu`
- `ir.actions.act_window` / `ir.actions.server` / `ir.actions.report` /
  `ir.actions.act_url` / `ir.actions.client`
- `ir.model.access` / `ir.rule`
- `ir.cron` / `ir.cron.trigger`
- `ir.config_parameter` (salvo re-aplicación controlada de claves DEV)
- `ir.sequence` **excepto** las ligadas a NCF/fiscal al sincronizar rangos
- `ir.attachment` de tipo asset/QWeb (usar filestore solo de adjuntos de negocio)
- `ir.asset` / `ir.binary` técnicos
- `ir.logging` / `ir.http` routing

### Seguridad y usuarios (definición)
- `res.groups` / `res.groups.privilege`
- `res.users` / `res.users.settings` (no sobrescribir usuarios DEV/UAT)
- `res.groups.users.rel` (reaplicar selectivamente post-install)
- ACL / record rules (cualquier tabla `ir_model_access`, `ir_rule`)

### Correo / integraciones / secretos
- `ir.mail_server`
- `fetchmail.server`
- Certificados, claves API, tokens (`justech.ecf.certificate`,
  `justech.ecf.api.token`, etc.) — **no** traer secretos de Prod a DEV
- SMTP, OAuth, webhooks, workers, certificados TLS del servidor

### Configuración Justech / producto
- `justech.admin.module` / `justech.admin.product` (catálogo: sale de XML)
- `justech.admin.module.company` (activar desde backup DEV, no desde Prod)
- `justech.feature` / `justech.feature.company`
- `justech.client.module.state` / `justech.client.module.feature.flag`
- `justech.license*` / `justech.activation.key`
- `justech.fiscal.feature.flag`
- `justech.ecf.company.config` (modo laboratorio DEV)
- `justech.do.ncf.range` / configuración activa de numeración Justech (DEV)
- `ir.sequence` ligada a numeración fiscal activa de DEV
- Settings de Garantías por compañía (campos `res.company` Justech warranty /
  datos XML de tipos: reinstalar módulo)
- Feature flags y activaciones por empresa

### Servidor / runtime
- `odoo.conf` / systemd / nginx / cron del SO
- Addons, código, ramas Git
- Workers, longpolling, redis config
- Filestore completo si incluye assets de módulos (preferir adjuntos de negocio)

## Por qué

Un `pg_restore` completo de Producción **borra** estados de módulos Justech,
vistas, menús, ACL y activaciones DEV. Eso no es un “refresh de datos”.

## Si ya ocurrió un restore completo (recuperación)

1. No restaurar toda la BD DEV anterior (perdería transacciones nuevas).
2. Instalar/actualizar módulos Justech desde addons.
3. Reaplicar desde backup pre-sync solo: activaciones, ECF lab config, flags de
   compañía, membresías de grupos Justech para logins existentes.
4. Validar conteos operativos vs snapshot post-restore Prod.
5. Documentar en evidence y actualizar allowlist/denylist si hace falta.

## Checklist pre-sync (obligatorio)

- [ ] ¿El job solo lista tablas/modelos de ALLOWLIST?
- [ ] ¿Denylist revisada?
- [ ] ¿Backup + restore-test DESTINO PASS?
- [ ] ¿Producción en solo lectura?
- [ ] ¿Plan de reinstall Justech + reactivaciones preparado?
