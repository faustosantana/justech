# BACKUP_MANIFEST — CHG-001 FortiGate CAPITAL

Backup maestro **privado**. El fichero `.conf` **no** está en GitHub ni en este repositorio.

| Campo | Valor |
|---|---|
| CHANGE-ID | CHG-001 |
| Autorización | `AUTORIZO CHG-001 ÚNICAMENTE` |
| Fecha/hora UTC (descarga) | 2026-09-15 20:43 |
| Método | GET READ-ONLY `/api/v2/monitor/system/config/backup?scope=global` (sesión GUI `admin` ya autenticada) |
| Save / Apply en el equipo | **No**. No se pulsó Save. `current_config_unsaved` no se forzó a false |
| Cambios de configuración en el FortiGate | **0** |

## Equipo (cabecera del backup, sin secretos)

| Campo | Valor |
|---|---|
| Hostname | CAPITAL |
| Serial / alias | FG100ETK19012927 |
| Plataforma | FG100E |
| FortiOS | v7.0.15 build0632 (`#config-version=FG100E-7.0.15-FW-build0632-240401`) |
| Usuario que exportó | admin |
| `#conf_file_ver` | 2099165266408538 |
| `#buildno` | 0632 |
| `#global_vdom` | 1 |

## Fichero privado

| Campo | Valor |
|---|---|
| Nombre | `CAPITAL_PRECHANGE_20260915_2043.conf` |
| Ubicación (solo este VM, modo 600) | `/home/ubuntu/private/fortigate-backups/CAPITAL_PRECHANGE_20260915_2043.conf` |
| Tamaño | 649162 bytes (633.9 KiB) |
| SHA-256 | `8573a6e43632a5582c7bfab44aa339687b4ebbd4902742a45aaf1b8166e2f2e6` |
| En git | **No** |

## Validación de integridad

| Comprobación | Resultado |
|---|---|
| Tamaño > 0 | OK |
| No es HTML de login | OK |
| No es JSON de error API | OK |
| Cabecera `#config-version=FG100E-7.0.15-FW-build0632-240401` | OK |
| `set hostname "CAPITAL"` | OK |
| Serial `FG100ETK19012927` en bloque global | OK |
| Secciones presentes: `system admin`, `system interface`, `firewall policy`, `wireless-controller vap`, `vpn ssl settings`, `switch-controller` | OK |
| Bytes nulos | No |
| Líneas | 18751 |
| SHA-256 recalculado tras copiar a la ruta privada | Coincide |

Este backup es la configuración **guardada** en flash. Había `current_config_unsaved=true` en la muestra forense; **no** se guardó esa sesión GUI, así que posibles ediciones no aplicadas **no** están en este fichero.

El `.conf` contiene secretos de dispositivo (hashes ENC, PSK, claves). No se reproducen aquí.

## Post-CHG-001 (no ejecutado)

CHG-002, cuenta `justech_cursor_audit`, desconexión de `support_fortinet`, disable de admins, MFA, Trusted Hosts, WAN, SD-WAN, Wi-Fi, FortiLink, DHCP, DNS y firewall: **no iniciados**. Esperan un `AUTORIZO CHG-XXX` nuevo.
