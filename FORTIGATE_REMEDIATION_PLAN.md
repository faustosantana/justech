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

## CHG-003 — Desconectar sesiones SSH de `support_fortinet` (**NO EJECUTADO**)

**PROBLEMA:** Sesiones SSH activas de una cuenta `super_admin` cuya legitimidad no está demostrada.

**EVIDENCIA (última API, 2026-09-15 20:52 UTC):** dos SSH `support_fortinet` desde `94.198.50.189` (wan1 id 22685, wan2 id 22690). Cuenta: MFA `disable`, Trusted Hosts `0.0.0.0/0` y `::/0`, perfil `super_admin`. RDAP SmartApe RU; no es ASN Fortinet TAC. No hay log de acciones. **No se reautenticó** en este paso para refrescar (GUI en login).

**CAMBIO PROPUESTO:** finalizar **únicamente** las sesiones activas de `support_fortinet` (API disconnect por session id, tras un GET fresco de `current-admins`). La cuenta permanece.

**NO:** borrar/deshabilitar la cuenta; cambiar password/MFA/Trusted Hosts; tocar otros admins; tocar WAN; tocar firewall.

**RIESGO:** Bajo/Medio. Si era soporte real, se reconectará. Si era abusivo, corta el acceso actual. Camino A (`admin` HTTPS) no se toca.

**ROLLBACK:** cuenta intacta; puede volver a autenticarse.

**VALIDACIÓN:** `support_fortinet` sesiones = 0; `admin` sigue conectado; WAN1/WAN2 UP; FortiLink UP; switches/AP online.

`¿AUTORIZAS CHG-003?`

---

## Prohibido hasta Camino B probado

Quitar HTTPS WAN, cambiar puerto 443, Trusted Hosts de `admin`, MFA/password de `admin`, borrar `admin`, tocar wan1 y wan2 a la vez, tocar ambos miembros FortiLink, firmware, factory reset.
