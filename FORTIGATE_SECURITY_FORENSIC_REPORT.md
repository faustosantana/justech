# Investigación forense READ-ONLY — administradores FortiGate CAPITAL

| Campo | Valor |
|---|---|
| Equipo | FortiGate 100E `CAPITAL` SN FG100ETK19012927 |
| FortiOS | v7.0.15 build0632 **CONFIRMADO** (re-verificado 2026-09-15 20:15 UTC) |
| Alcance | Cuentas `system.admin`, sesiones, API users, logs, IoC |
| Cambios realizados | **0** |
| Credenciales almacenadas | **0** |

Muestras de sesión:

- 2026-09-15 ~18:12 UTC (auditoría previa)
- 2026-09-15 ~20:15 UTC (esta investigación)

---

## ¿HAY EVIDENCIA DE COMPROMISO?

**INCONCLUSO**

Hay **indicadores de alto riesgo y persistencia posible** (42 `super_admin`, nombres que imitan Fortinet, SSH activo desde hosting ruso, API keys `super_admin`, admin WAN abierto). **No hay prueba forense de que un atacante creó esas cuentas ni de comandos maliciosos**, porque el equipo **no conserva historial de eventos de administración consultable**.

No se clasifica **COMPROMISO CONFIRMADO**.  
No se clasifica **NO** (la hipótesis de compromiso **no está descartada**).

### Qué logs faltan (causa del INCONCLUSO)

| Fuente | Estado | Clase |
|---|---|---|
| Disco de logs | `log_disk_status=not_available`; disk logging disable | CONFIRMADO |
| Eventos GUI System/User | “No results” con filtro login | CONFIRMADO |
| API `log/memory/event` | 404 | CONFIRMADO |
| API `log/forticloud/event` | 404 | CONFIRMADO |
| Syslog 1–4 | **status=disable**, server vacío | CONFIRMADO (corrige una inferencia anterior de “syslog activo”) |
| FortiAnalyzer | status=disable, server vacío | CONFIRMADO |
| FortiCloud logging device flag | `forticloud.is_enabled=true` pero sin eventos vía API | CONFIRMADO flag / eventos **NO VERIFICADOS** |
| Config revision | Solo 4 snapshots (2021 rating + 2024 upgrade) | CONFIRMADO |
| `system.auto-script` | API 405 | **NO VERIFICADO** |

Sin syslog/FAZ/eventos no se puede responder quién creó cada cuenta, desde qué IP, ni qué cambió `support_fortinet`.

---

## `support_fortinet` — veredicto

**Clasificación: SOSPECHOSO / LEGITIMIDAD NO DEMOSTRADA**

No es **LEGÍTIMO CONFIRMADO** (el nombre no basta; no es ASN Fortinet).  
No es **COMPROMISO CONFIRMADO** (no hay log de acciones).

| Pregunta | Hallazgo | Clase |
|---|---|---|
| ¿Sesión todavía existe? | Sí. Dos SSH concurrentes, wan1 id 22122 y wan2 id 22127 | CONFIRMADO 20:15 UTC |
| Protocolo / interfaz | SSH / wan1 **y** wan2 | CONFIRMADO |
| IP | `94.198.50.189` en ambas | CONFIRMADO |
| ¿Misma sesión desde las 18:12? | **No.** A las 18:12 ids 20705/20717; a las 20:15 ids 22122/22127 → reconexión | CONFIRMADO |
| MFA | `two-factor=disable` | CONFIRMADO |
| Trusted Hosts | 0.0.0.0/0 y ::/0 | CONFIRMADO |
| SSH public key en la cuenta | campo vacío en volcado | CONFIRMADO (con la salvedad de que un redact excesivo previo no aplica a este dump) |
| Comentarios / email | vacíos | CONFIRMADO |
| Creación | **CREATOR UNKNOWN** | CONFIRMADO ausencia de evidencia |
| RDAP IP | bloque 94.198.50.0/24 **SmartApe**, país **RU**, abuse smartape.ru | CONFIRMADO whois; **no prueba** por sí sola de ataque |
| ¿Es TAC Fortinet? | **PROBABLE que no** (hosting comercial RU, no rango Fortinet documentado aquí) | PROBABLE |

**No se desconectó la sesión. No se deshabilitó la cuenta.**

---

## Inventario de 42 administradores

Todos **CONFIRMADOS** en `GET /api/v2/cmdb/system/admin` (20:15 UTC):

- Perfil: **super_admin** (42/42)
- VDOM: root
- remote-auth: disable (locales)
- wildcard: disable
- Trusted Hosts IPv4: `0.0.0.0 0.0.0.0`
- Trusted Hosts IPv6: `::/0`
- SSH key: no presente
- Comentarios: vacíos
- MFA: **solo `admin` y `justech`** (`two-factor=fortitoken`). El serial del token **no se documenta** (secreto).

Detalle tabular: `FORTIGATE_ADMIN_ACCOUNTS.csv`

| Clase | n | Ejemplos |
|---|---|---|
| A — LEGÍTIMA CONFIRMADA | 1 | `admin` (sesión del propietario + auditoría) |
| B — PROBABLEMENTE LEGÍTIMA | 2 | `justech` (MFA; contexto Justech), `fsantana` (email `fausto@capitaldbg.com` en user local homónimo) |
| C — DESCONOCIDA | 6 | `IT-SUPPORT`, `IT_Admin`, `Soporte`, `data_noc`, `djohn`, `emad` |
| D — SOSPECHOSA | 33 | `support_fortinet`, `fortinet-exdyb/gebtq/itzfo/knhhe/mkoqd/rxext/untqm/wgnud`, `Forti_Support`, `fgtsupport`, `oldadmin`, `admin2`, `system`, `ldap`, `forti-autosync`, cuentas VPN extra, etc. |
| E — EVIDENCIA DE COMPROMISO | 0 | — |

**Creator:** **CREATOR UNKNOWN** para las 42. Las revisiones de config no listan altas de admin.

Uso observado (solo dos ventanas de ~2 h):

| Cuenta | Actividad observada |
|---|---|
| `admin` | HTTPS wan1. 18:12 desde 16.58.190.11 (sesión auditoría previa). 20:15 desde **170.244.42.35** (probable tú) y **3.151.173.70** (sesión Cursor/cloud). |
| `support_fortinet` | SSH dual-WAN 94.198.50.189 en **ambas** muestras, con IDs distintos |
| Las otras 40 | **Sin login** en esas muestras. Historial largo: **NO VERIFICADO** |

`FORTIGATE_ADMIN_ACTIVITY.csv`

---

## Otros IoC (sin remediar)

Ver `FORTIGATE_IOC_REVIEW.csv`. Resumen:

1. **API users** `apiuser` y `rest-admin`, ambos `super_admin`, trusthost vacío, api-key presente (redactada). CONFIRMADO.  
2. **SSL-VPN** enable, puerto 19543, `source-interface=any`, TLS 1.1, 0 sesiones ahora. CONFIRMADO.  
3. **HTTPS+SSH en wan1 y wan2.** Re-verificado. CONFIRMADO.  
4. **Syslog off** — la auditoría Wi-Fi anterior **no** debe usarse como “hay 4 syslog”. CONFIRMADO disable.  
5. **VIP WAN:** 8443/443/48620 → 10.0.0.12; 8000 → 10.0.0.51 (cámaras). CONFIRMADO. No se toca.  
6. **45 user/local** (VPN/portal), no son `system.admin`. LDAP/RADIUS vacíos. CONFIRMADO.  
7. **SNMP disable**, 0 communities. CONFIRMADO — no hay backdoor SNMP visible.  
8. **CSF disable.** Automation: plantillas Fortinet + stitch `Seguridad clasificacion` enable (email/iOS). CONFIRMADO.  
9. **FortiGate Cloud:** central-management type fortiguard; FMG status `up` / `registered` sn `fortigatecloud.fort`; **allow-push-firmware y allow-push-configuration = enable**. CONFIRMADO.  
10. **`current_config_unsaved=true`.** No se pulsó Save. Causa **NO VERIFICADA** (posible GUI de la otra sesión `admin`).  
11. **Alertemail:** `admin-login-logs=disable`, `ssh-logs=disable`, `configuration-changes-logs=disable`. CONFIRMADO — no alertaría este SSH.  
12. Scripts CLI persistentes: **NO VERIFICADO**.

FortiOS 7.0.15 no se declara comprometido “por versión”. El patrón de muchos `super_admin` + SSL-VPN público es **compatible** con persistencia post-incidente histórico, no es prueba.

---

## Re-verificación de hechos de la auditoría previa

| Hecho previo | Ahora |
|---|---|
| 42 super_admin | **CONFIRMADO** |
| MFA solo 2 cuentas | **CONFIRMADO** (`admin`, `justech`) |
| Trusted Hosts abiertos | **CONFIRMADO** también IPv6 ::/0 |
| HTTPS/SSH WAN | **CONFIRMADO** |
| `support_fortinet` 94.198.50.189 | **CONFIRMADO** y persistente (reconecta) |
| Syslog “activo” | **FALSO / corregido:** disable |
| FortiGuard expirado | no re-chequeado licencia completa en este paso; **NO RE-VERIFICADO** aquí |
| WAN1 jitter/loss | **CONFIRMADO de nuevo:** wan1 loss **3 %**, jitter ~46 ms; wan2 loss 0 %, jitter ~16 ms (wan2 peor que a las 18:12) |
| FortiLink port11 | **no re-muestreado** en este paso (fuera de alcance forense) |

---

## Acceso remoto (no tocar)

- Camino A: HTTPS `admin` por WAN — **funcional**.  
- No se restringió Trusted Hosts de `admin`.  
- No se cerró SSH (haría falta para `support_fortinet`, y es un cambio de contención **no autorizado**).  
- IP cloud de esta sesión: `3.151.173.70` (efímera; **no** sirve como Trusted Host estable).

---

## Pasos 4–9 (estado)

| Paso | Estado |
|---|---|
| 1 Reauth manual | Hecho por el propietario |
| 2 Forense 42 admins + support_fortinet | **Hecho READ-ONLY** |
| 3 Entrega evidencia | Este informe + CSV |
| 4 Backup maestro | **CHG-001 completado** (privado, no git). Ver `BACKUP_MANIFEST.md` |
| 5 Validar backup | **OK** — 649162 bytes, SHA-256 en manifiesto |
| 6–8 Usuario `justech_cursor_audit` | Pendiente de backup + autorización CHG-002 + contraseña tuya |
| 9 Remediación | **No iniciada** |

---

## Primer cambio recomendado

**CHG-001: backup maestro privado** (no Git, no secretos en el repo).  
Después: CHG-002 cuenta READ-ONLY, **sin** cerrar `admin`.  
Contención de `support_fortinet`: solo tras tu `AUTORIZO CHG-xxx` y un plan de no perder el Camino A.

**No se eliminó ni deshabilitó ninguna cuenta.**
