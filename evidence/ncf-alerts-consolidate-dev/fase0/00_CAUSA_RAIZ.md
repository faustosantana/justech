# FASE 0 — Causa raíz: ruido de alertas NCF

Fecha: 2026-07-16  
Entorno: DEV `justech_dev` @ `207.244.242.58`  
Backup: `/opt/odoo-dev/backups/ncf-alerts-consolidate-dev-20260716_222539`  
Restore test: PASS

## Dónde se genera el ruido

Archivo: `custom/justech_l10n_do_ncf/models/ncf_range.py`

| Método | Efecto |
|---|---|
| `_cron_process_ncf_range_alerts` | Recorre **cada rango** de cada empresa |
| `_process_alerts` | Evalúa umbrales **por rango** |
| `_emit_alert` | Por cada rango en alerta: |
| → `activity_schedule` en bucle | **1 actividad × cada usuario** destinatario |
| → `message_post(..., partner_ids=..., subtype=mail.mt_comment)` | Dispara **notificación/correo** a partners |

## Por qué hay correo + actividad

1. **Actividad**: `activity_schedule` crea `mail.activity` (bandeja).
2. **Correo**: `message_post` con `partner_ids` + `mail.mt_comment` genera notificación de mensaje (y correo si el usuario tiene preferencias de email). No hay `mail.mail` explícito ni plantilla custom, pero el chatter **sí** provoca envío externo.

## Por qué HTML se ve como texto

La `note` de la actividad se arma con string HTML (`<p><ul><li>`), pero sin `markupsafe.Markup` / formato correcto puede mostrarse escapado o como texto plano en algunos clientes de actividad.

## Por qué hay muchos avisos

- Idempotencia actual es **por rango** (`alert_*_cycle` en cada `justech.do.ncf.range`).
- Un responsable con acceso a una empresa recibe N actividades + N mensajes si hay N rangos en umbral.
- Varios grupos (Responsable Fiscal + Administrador Fiscal + Settings) multiplican actividades.

## Corrección acordada

- Solo actividad interna consolidada **1 por empresa**.
- Cero `message_post` con destinatarios en el flujo de alertas.
- Cero plantillas / `mail.mail` / `force_send` para alertas NCF.
- Nota HTML con `Markup`, textos/botones en español.
- Idempotencia por empresa + ciclo consolidado.
