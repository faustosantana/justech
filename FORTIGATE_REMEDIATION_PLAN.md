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

**Re-verificación 22:20 UTC (GET fresco, pestaña nueva):** reconectó. Ver CHG-004.

---

## CHG-004 — Bloquear login remoto de `support_fortinet` (**EJECUTADO** 2026-09-15 22:29 UTC)

**EVIDENCIA FRESCA 22:20 UTC:** SSH wan1 id **23846** y wan2 id **23848**, origen `94.198.50.189`. No es TAC Fortinet.

**FortiOS 7.0.15:** `GET system.admin` **no** incluye campo `status`. PUT `{status:disable}` devolvió 200 pero **no persistió** (trusthost seguía abierto). No se borró la cuenta. No se cambió password.

**ACCIÓN EFECTIVA:** PUT solo sobre `support_fortinet`:
- `ip6-trusthost1` = `::1/128`
- `trusthost1` = `192.0.2.1 255.255.255.0` (TEST-NET-1; máscara /32 host fue rechazada por el parser 7.0)

**VALIDACIÓN:** GET fresco `current-admins` = 3× `admin` HTTPS, **0** `support_fortinet`. WAN1/WAN2/port14 UP; 6 AP; 6 switch Connected. `admin` / `justech` / `fsantana` no tocados.

**ROLLBACK:** PUT `trusthost1=0.0.0.0 0.0.0.0` y `ip6-trusthost1=::/0` en esa cuenta únicamente.

---

## Fase 5 — Quitar `ssh` de wan1 luego wan2 (**EJECUTADO** 2026-09-15 22:29 UTC)

**Hecho de uno en uno.** wan1 `ping https ssh` → `ping https` (PUT 200, HTTPS validado). Luego wan2 `ping https ssh fabric` → `ping https fabric` (PUT 200). IPs, gateways, rutas, SD-WAN, FortiLink, HTTPS: **no tocados**.

**ROLLBACK por WAN:** restaurar el `allowaccess` previo de esa interfaz.

---

## Fase 6 — Muestra WAN (**sin cambio de SLA**)

GET 22:33 UTC TRICOM_HC: wan1 ~23 ms / jitter 2.7 / loss 2 %; wan2 ~26 ms / jitter 0.08 / loss 0 %. No se cambió SD-WAN.

---

## Fase 8 — Canal 2.4 ACV (**NO APLICADO**)

PUT per-AP `override-channel` en `FP221E5520099ACV` → HTTP 500. Rollback 200. AP siguió en ch 6/132, 6 AP online. No se tocó el perfil compartido FORALL.

**No reintentar el mismo PUT.** El schema 7.0.15 en WTP es `radio-1.override-channel=enable` + `radio-1.channel=[{chan:"11"}]`, no un entero suelto. Ver `FORTIGATE_WIFI_SETTING_MAP.md`.

---

## Continuación A–K (2026-09-15 22:47 UTC) — **STOP reauth**

Sesión GUI `admin` viva a las 22:53. A las 23:05 la API sin cookie responde **401**. FortiGate HTTPS **sigue arriba**. No se ejecutaron writes de SD-WAN, DHCP, DNS, 802.11k/v ni background scan.

Tras reauth manual, retomar en este orden: A (current-admins fresco) → C (5 muestras WAN) → D/E (lease 8h + DNS 1.1.1.1 por scope) → G (11k/v en VAP `Empleados` primero) → J (delta FortiLink). No RF hasta mapping + datos nuevos + rollback por AP.

---

## Prohibido hasta Camino B probado

Quitar HTTPS WAN, cambiar puerto 443, Trusted Hosts de `admin`, MFA/password de `admin`, borrar `admin`, tocar wan1 y wan2 a la vez, tocar ambos miembros FortiLink, firmware, factory reset.
