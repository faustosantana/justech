# Configuración del sistema — Hellenia Odoo 19

**Fecha revisión:** 2026-06-30  
**Ambientes:** DEV, TEST

---

## 1. Empresa

| Parámetro | Valor DEV/TEST | Estado |
|-----------|----------------|--------|
| Razón social | Hellenia, S.R.L. | ✅ |
| RNC | 133621282 | ✅ |
| País | República Dominicana (DO) | ✅ |
| Moneda | DOP | ✅ |
| Correo empresa | info@helleniadr.com | ✅ |
| Teléfono | +1 849-434-8694 | ✅ |
| Logo | Configurado | ✅ |
| Fiscal Justech habilitado | Sí | ✅ |
| Compañías en instancia | 1 | ✅ |

---

## 2. Regionalización

| Parámetro | Valor |
|-----------|-------|
| Idioma instalado `es_DO` | Activo |
| Idioma usuarios operativos | `es_DO` |
| Zona horaria | `America/Santo_Domingo` |
| Localización RD | `l10n_do` instalado |

---

## 3. Parámetros web (`ir.config_parameter`)

| Clave | DEV | TEST |
|-------|-----|------|
| `web.base.url` | `https://dev.hellenia.cloud` | `https://test.hellenia.cloud` |
| `database.is_neutralized` | — | `true` |
| `database.enterprise_code` | Registrado (DEV licencia) | Heredado / neutralizado |
| `mail.catchall.domain` | No configurado | No configurado |
| `mail.default.from` | No configurado | No configurado |
| `mail.bounce.alias` | No configurado | No configurado |
| `mail.catchall.alias` | No configurado | No configurado |

### `proxy_mode`

```ini
# config/dev/odoo.conf y config/test/odoo.conf
proxy_mode = True
```

Traefik termina TLS y reenvía a Odoo:8069.

---

## 4. Correo / SMTP

| Item | DEV | TEST |
|------|-----|------|
| Servidores salientes (`ir.mail_server`) | 0 | 0 |
| Envío real habilitado | Sí (riesgo sin SMTP) | No (neutralizado) |

**Pendiente UAT:** configurar SMTP corporativo (ej. Microsoft 365 / Google Workspace) con:
- Servidor saliente
- `mail.default.from` = `noreply@helleniadr.com` o similar
- `mail.catchall.domain` = `helleniadr.com`

---

## 5. Nombre de instancia

| Ambiente | URL oficial | BD |
|----------|-------------|-----|
| DEV | https://dev.hellenia.cloud | `hellenia_dev` |
| TEST | https://test.hellenia.cloud | `hellenia_test` |
| PROD futura | https://odoo.hellenia.cloud | Por definir |

---

## 6. Módulos instalados (112)

Núcleo comercial + Enterprise + Justech MVP:

- `justech_l10n_do_base` `19.0.1.1.0`
- `justech_l10n_do_ncf` `19.0.1.1.0`
- `justech_l10n_do_reports` `19.0.1.1.0`

**No instalado:** `point_of_sale`, módulos CRM/helpdesk prohibidos por política Hellenia.

---

## 7. Backups

| Ambiente | Último backup | Ruta |
|----------|---------------|------|
| DEV | 2026-06-30 12:10 | `backups/dev/2026-06-30_1210` |
| TEST | 2026-06-30 12:18 | `backups/test/2026-06-30_1218` |

Scripts: `backup-dev.sh`, `backup-test.sh`, `verify-backup-dev.sh`

Retención: 7 días diarios / 4 semanales / 6 mensuales.

---

## 8. Logs

| Fuente | Ubicación | Nivel |
|--------|-----------|-------|
| Odoo DEV | stdout Docker | `debug` |
| Odoo TEST | stdout Docker | `info` |
| Scripts deploy | `logs/deploy/` | texto |
| Traefik | stdout contenedor | INFO |

**Sin errores CRITICAL** en contenedores DEV/TEST al cierre Fase 7.5.

Rotación: pendiente logrotate VPS (documentado en INFRASTRUCTURE_REVIEW).

---

## 9. Scheduled Actions (cron)

| Ambiente | Activos | Inactivos |
|----------|---------|-----------|
| DEV | 29 | 5 |
| TEST | Similar (neutralizado) | — |

Crons críticos documentados en [SECURITY_AUDIT.md](SECURITY_AUDIT.md) §7.

---

## 10. Pendientes de configuración

| # | Item | Antes de |
|---|------|----------|
| 1 | SMTP corporativo | UAT con notificaciones |
| 2 | Alias catchall/bounce | UAT correo entrante |
| 3 | Política contraseñas / 2FA | UAT usuarios negocio |
| 4 | Desactivar o restringir `admin` post-UAT | Go-Live |
| 5 | Logo/alta resolución verificado en PDF NCF | UAT |

---

## 11. Verificación

```bash
./scripts/audit-company-config.py   # vía odoo shell
./scripts/audit-security-phase75.sh dev
./scripts/audit-security-phase75.sh test
```
