# Plan de remediación — FortiGate CAPITAL

**Ningún CHG se ejecuta hasta `AUTORIZO CHG-XXX`.**

Prioridad remota: no perder HTTPS WAN ni la cuenta `admin`.

- **Camino A (CONFIRMADO):** HTTPS/443 en wan1 y wan2, usuario `admin` + FortiToken.
- **Camino B independiente:** **NO PROBADO** (SSL-VPN 19543 con 0 sesiones; mgmt 192.168.0.99 sin link). No se cierra Camino A.

---

## CHG-001 — Backup maestro (**COMPLETADO** 2026-09-15 20:43 UTC)

**PROBLEMA:** no hay copia recuperable controlada antes de cualquier cambio.

**EVIDENCIA:** forense de admins completada; `current_config_unsaved=true` (no pulsar Save).

**CONFIGURACIÓN ACTUAL:** N/A.

**CAMBIO PROPUESTO:** descargar configuración completa a fichero **privado** `CAPITAL_PRECHANGE_YYYYMMDD_HHMM.conf`. No GitHub. No commit.

**COMANDOS/ACCIONES EXACTAS:** en sesión `admin` ya autenticada, GET de backup FortiOS 7.0.15 (`/api/v2/monitor/system/config/backup?scope=global` o descarga GUI equivalente, verificado en el momento). Calcular SHA-256. Escribir `BACKUP_MANIFEST.md` sin pegar secretos.

**RIESGO:** bajo (solo lectura). Si el GET fallara, no hay cambio en el equipo.

**RIESGO DE PERDER ACCESO REMOTO:** BAJO

**IMPACTO SOBRE CLIENTES:** ninguno

**VENTANA REQUERIDA:** no

**ROLLBACK EXACTO:** no aplica (solo archivo local)

**PRUEBAS PRE-CAMBIO:** GUI `admin` viva; no estamos en pantalla de login.

**PRUEBAS POST-CAMBIO:** archivo no vacío; tamaño > 0; SHA-256; hostname/serial visibles en cabecera sanitizada del manifiesto.

**CRITERIO DE ÉXITO:** manifiesto válido, backup fuera de git.

**CRITERIO DE ROLLBACK:** N/A

**Ejecutado.** Manifiesto: `BACKUP_MANIFEST.md`. Fichero `.conf` **no** está en git. No se pulsó Save.

`CHG-002` **no** se pide ni se ejecuta en este paso.

---

## CHG-002 — Usuario READ-ONLY `justech_cursor_audit`

**CANCELADO POR DECISIÓN OPERATIVA** (2026-09-15 21:13 UTC). No es un fallo técnico pendiente. No se creó el usuario ni perfiles nuevos. `admin` sigue siendo la cuenta operativa.

---

## CHG-003 — Desconectar sesiones SSH de `support_fortinet` (**EJECUTADO** 2026-09-15 22:02 UTC)

**PROBLEMA:** Sesiones SSH activas de una cuenta `super_admin` cuya legitimidad no está demostrada.

**EVIDENCIA PRE-CAMBIO (GET `current-admins` ~22:00 UTC):** dos SSH `support_fortinet` desde `94.198.50.189` (wan1 id **23515**, wan2 id **23530**). (IDs anteriores en la misma investigación: 22685/22690, 23443/23453 — la cuenta **reconectaba**.) MFA `disable`, Trusted Hosts `0.0.0.0/0` y `::/0`, perfil `super_admin`. RDAP SmartApe RU; no es ASN Fortinet TAC.

**ACCIÓN:** POST `/api/v2/monitor/system/disconnect-admins/select` con `{"admins":[{"id":23515,"method":"ssh"},{"id":23530,"method":"ssh"}]}`. Header `X-CSRFTOKEN` = valor de cookie `ccsrftoken` **sin comillas**. HTTP **200**.

**NO HECHO:** borrar/deshabilitar la cuenta; password/MFA/Trusted Hosts; otros admins; WAN allowaccess; firewall.

**VALIDACIÓN INMEDIATA:** `after_admins` = tres HTTPS `admin` (369090 `170.244.42.35`, 370912 `18.217.23.204` is_current, 370829 `3.15.75.171`). 0 SSH `support_fortinet`. WAN1/WAN2 UP 1G; port14 UP; port11 down (visita física); 6 AP + 1 discovered; 6 switch Connected + FS224D3Z15000948 Idle; 70 clientes Wi-Fi.

**ROLLBACK:** no aplica a config; la cuenta puede volver a autenticarse (si reconecta desde `94.198.50.189` u otra IP desconocida → **CHG-004** disable **solo** esa cuenta).

**Re-verificación 22:08 UTC:** **NO VERIFICADA** — Chrome VM otra vez en Login/401. Las pestañas JSON de `current-admins` son caché, no GET vivo.

---

## CHG-004 — Disable `support_fortinet` si reconecta (**NO EJECUTADO**)

Solo si GET fresco muestra esa cuenta SSH/HTTPS desde `94.198.50.189` o IP no reconocida. No tocar `admin` / `justech` / `fsantana`. No borrar. No masivo de 42 admins.

---

## Fase 5 — Quitar `ssh` de wan1 luego wan2 (**NO EJECUTADO** — STOP Fase 0)

Prior allowaccess confirmado en GET 22:00: wan1 `ping https ssh` → objetivo `ping https`. wan2 `ping https ssh fabric` → objetivo `ping https fabric`. HTTPS se conserva. IPs/gateway/rutas **no** se tocan. Requiere sesión `admin` viva en este Chrome.

---

## Prohibido hasta Camino B probado

Quitar HTTPS WAN, cambiar puerto 443, Trusted Hosts de `admin`, MFA/password de `admin`, borrar `admin`, tocar wan1 y wan2 a la vez, tocar ambos miembros FortiLink, firmware, factory reset.
