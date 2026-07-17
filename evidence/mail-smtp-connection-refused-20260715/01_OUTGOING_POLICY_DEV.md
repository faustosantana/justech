# Política permanente From/Reply-To — validación DEV

Fecha: 2026-07-15 (UTC)

## Declaración operativa

1. **Qué:** Módulo `justech_mail_outgoing_policy` 19.0.1.0.0  
2. **Por qué:** Evitar `SendAsDenied` (M365) y cumplir From=`notifications@` + Reply-To=usuario  
3. **Riesgos:** Bajo en DEV (sink); en Prod solo tras aprobación  
4. **Backup:** N/A código; DB DEV desechable/clon  
5. **Rollback:** `justech_mail.outgoing_policy_enabled=False` o desinstalar módulo  
6. **Archivos:** `custom/justech_mail_outgoing_policy/**`  
7. **Módulos:** solo `justech_mail_outgoing_policy` (depends `mail`)  
8. **Tiempo:** ~30–45 min  

## Entorno

| Campo | Valor |
|---|---|
| Host | `erp.justech.do` / `207.244.242.58` |
| DB | `justech_dev` |
| Servicio | `odoo-dev` (reiniciado tras install) |
| SMTP | Neutralization `localhost:1025` + `dev_smtp_sink.py` |

## Resultado DEV

| Prueba | From resultante | Reply-To | state |
|---|---|---|---|
| Usuario `administracion@` | `Notificaciones Justech <notifications@justech.do>` | `Diana Ayala <administracion@justech.do>` | sent |
| Usuario `recepcion@` (post-restart) | `Notificaciones Justech <notifications@justech.do>` | `Jennipher Martínez <recepcion@justech.do>` | sent |

Módulo: `installed | 19.0.1.0.0`

## Producción

**No desplegado.** Espera aprobación explícita.
