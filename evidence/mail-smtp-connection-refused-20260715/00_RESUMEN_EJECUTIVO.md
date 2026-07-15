# Incidente correo saliente — Connection refused (2026-07-15)

## Entorno afectado

| Campo | Valor |
|---|---|
| Entorno | **Producción** |
| Host | `justgroup` / `31.97.6.178` (`justgroup.app`) |
| Base de datos | `justech` |
| Servicio | `odoo` (activo) |
| Config | `/etc/odoo/odoo.conf` |
| Último error previo al fix | `2026-07-15 22:23:38 UTC` — `mail.mail` id **2651** — Errno **111 Connection refused** |

DEV (`erp.justech.do` / `justech_dev`) **no** es el origen del fallo de negocio: mantiene SMTP de neutralización `localhost:1025` con sink activo.

## Causa raíz exacta

1. Los **5** servidores SMTP reales de Microsoft 365 / Outlook estaban **`active = false`** (desactivados el **2026-07-13**, notificaciones id 11 a las 23:56 UTC).
2. En el host **no hay MTA local** (nada escucha en 25/465/587).
3. Odoo, sin servidor saliente activo, intentaba **`localhost:25`** → **Errno 111 Connection refused**.

No era fallo de DNS ni cierre de `smtp.office365.com:587` (TCP + STARTTLS OK desde el VPS).

## Host/puerto del rechazo

- **Rechazo:** `127.0.0.1` / `localhost` puerto **25**
- **¿Localhost?** Sí (fallback), sin Postfix/Exim/Sendmail.

## Proveedor SMTP correcto

- **Microsoft 365** con autenticación **Outlook OAuth** ya configurada en Odoo (`smtp_authentication = outlook`).
- Servidor corporativo primario: id **11** `Notificaciones` → `smtp.office365.com:587` STARTTLS, usuario `notifications@justech.do`.
- Multi-empresa: id **12** `SMTP Just Office` → `smtp.outlook.com:587` STARTTLS, dominio `just-offices.com`.

## Cambio realizado (mínimo)

Backup metadatos (sin secretos): `/opt/odoo-backups/mail-smtp-fix-20260715_222800/`

| ID | Acción |
|---|---|
| 11 | `active=true`, `from_filter=justech.do`, `sequence=5` |
| 12 | `active=true`, `from_filter=just-offices.com`, `sequence=6` |
| 6,7,14 | Permanecen inactivos (archivados) |

No se modificaron módulos, plantillas, NCF, e-CF, ventas, facturación ni Helpdesk. No se borró la cola. No se reinició Odoo.

## Resultados de prueba

| Prueba | Resultado |
|---|---|
| `test_smtp_connection` id 11 | **PASS** (OAuth access token renovado) |
| `test_smtp_connection` id 12 | **PASS** (OAuth access token renovado) |
| Correo interno nuevo id 2652 → `fausto@justech.do` | **PASS** `state=sent` vía servidor **#11** |
| Reintento cola id 2643 → `it@justech.do` (helpdesk interno) | **PASS** enviado vía **#11** (registro auto-borrado por `auto_delete`) |

## Cola

| Momento | exception | sent | cancel |
|---|---|---|---|
| Tras diagnóstico | 422 | 1 | 1 |
| Tras pruebas | **421** | **2** | 1 |

- Reintentados con éxito: **1** correo de cola (2643) + **1** correo de prueba nuevo (2652).
- **No** se liberó la cola masiva (~421 remaining). Muchos tienen `email_to` vacío (destinatarios vía notificación/partner) y conviene inspección selectiva antes de reintento.

## Cron

- `Mail: Email Queue Manager` (**id 3**): **activo**, intervalo 1 hora.
- Fetchmail y demás crons de correo: activos (detalle en backup `mail_crons.txt`).

## DEV

| Check | Estado |
|---|---|
| Servidor activo | id **15** Neutralization → `localhost:1025` |
| Sink | `dev_smtp_sink.py` escuchando `127.0.0.1:1025` |
| Envío real M365 en DEV | **No** (SMTPs Office365 inactivos / sink activo) |

## Rollback

Documentado en el servidor: `/opt/odoo-backups/mail-smtp-fix-20260715_222800/ROLLBACK.md`

## Confirmaciones

- Módulos Python/XML: **ninguno modificado** en este incidente.
- NCF / e-CF / ventas / facturación / Helpdesk (código y lógica fiscal): **no afectados**.
- Secretos/tokens/contraseñas: **no** puestos en Git ni en esta evidencia.

## Reproceso cola 14–15 jul (completado)

Política aplicada al reenvío (y recomendada a futuro):

- **From:** `Notificaciones Justech <notifications@justech.do>`
- **Reply-To:** correo del usuario que generó la acción (nunca `odoobot@example.com` / `catchall@justech.do`)
- **No** intentar “Send As” con buzones individuales (M365 lo rechaza: `554 5.2.252 SendAsDenied`)

| Ventana | Resultado |
|---|---|
| `create_date >= 2026-07-14` | **0** excepciones restantes (reenviados OK) |
| Anteriores a 14 jul | **366** excepciones **sin tocar** |

Ejemplos Reply-To usados: `recepcion@`, `marieli@`, `soporte@`, `finanzas@`, `fausto@`, `administracion@`.

## Pendiente (requiere aprobación)

1. **Fix permanente** para correos nuevos: forzar From=`notifications@` + Reply-To=usuario (hoy Odoo sigue poniendo el buzón del usuario en From y M365 lo rechaza).
2. Cola antigua (>366) — dejar / cancelar / inventariar.
3. Plug Safe (id 14) sigue inactivo.
4. Confirmación humana de recepción de pruebas (`fausto@` / `it@`).
