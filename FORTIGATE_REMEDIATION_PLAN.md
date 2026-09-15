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

## CHG-002 — Usuario READ-ONLY `justech_cursor_audit` (después de CHG-001)

No se pide autorización todavía. Condiciones:

- Backup CHG-001 validado.
- Inspección de perfiles: existen `super_admin_readonly`, `Solo vista`, `admin_no_access`, `prof_admin`.
- Preferir perfil RO existente; si no cubre AP/Switch, crear `justech_cursor_ro` (WRITE none).
- Contraseña: **tú la introduces**; no se inventa ni se guarda.
- Trusted Host: **no** usar `3.151.173.70` (AWS efímera) sin tu decisión. Si no hay IP estable, detener y listar opciones.
- No asignar FortiToken de `admin`.
- No cerrar sesión `admin`. Segunda sesión para probar RO.
- Si el RO falla, no se toca `admin`.

Riesgo de acceso: MEDIO si TH/perfil mal — por eso Camino A permanece.

---

## Contención `support_fortinet` (no es CHG aún)

Opciones a discutir **después** del backup, una por una:

1. Solo observar (estado actual).
2. Desconectar las 2 sesiones SSH **sin** borrar la cuenta (impacto: si era soporte real, se quejan; si era abusivo, corta C2). Riesgo de acceso **bajo** para nosotros (no es nuestra sesión HTTPS).
3. Disable de la cuenta (más agresivo).
4. Borrar: **último recurso**, prohibido ahora.

No se hace 2–4 sin `AUTORIZO CHG-xxx` y confirmación de que **no** es un contrato de soporte activo.

---

## Prohibido hasta Camino B probado

Quitar HTTPS WAN, cambiar puerto 443, Trusted Hosts de `admin`, MFA/password de `admin`, borrar `admin`, tocar wan1 y wan2 a la vez, tocar ambos miembros FortiLink, firmware, factory reset.
