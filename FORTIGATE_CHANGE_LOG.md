# Registro de cambios — FortiGate CAPITAL

Configuración persistente del FortiGate: **sin cambios de allowaccess / cuentas / WAN / Wi-Fi**. CHG-003 desconectó sesiones SSH (no es cambio de config).

| Fecha/hora UTC | CHANGE-ID | Autorización | Estado previo | Acción | Resultado | Pruebas | Rollback | Estado final |
|---|---|---|---|---|---|---|---|---|
| 2026-09-15 20:15 | — | Investigación forense READ-ONLY | 42 admin, sesión support_fortinet SSH activa | GET API / GUI logs | Completado; compromiso INCONCLUSO | Sesión admin HTTPS viva; 0 Apply/Save | No aplica | Sin cambios en el FortiGate |
| 2026-09-15 20:43 | CHG-001 | AUTORIZO CHG-001 ÚNICAMENTE | Sin backup maestro controlado; `current_config_unsaved=true` | GET `/api/v2/monitor/system/config/backup?scope=global` (sesión `admin`) | Backup privado 649162 bytes SHA-256 `8573a6e43632a5582c7bfab44aa339687b4ebbd4902742a45aaf1b8166e2f2e6` | Cabecera FG100E 7.0.15 build0632 hostname CAPITAL serial FG100ETK19012927; no HTML; no Save | No aplica (solo archivo local) | Equipo sin cambios; `.conf` fuera de git |
| 2026-09-15 21:13 | CHG-002 | CANCELADO POR DECISIÓN OPERATIVA | Usuario RO no creado | Ninguna | Cancelado; `admin` permanece cuenta operativa | No se pulsó Create/POST | No aplica | 0 cambios; no `justech_cursor_audit` |
| 2026-09-15 22:02 | CHG-003 | Plan 23 fases (disconnect SSH `support_fortinet` únicamente) | SSH dual-WAN ids 23515 (wan1) y 23530 (wan2) desde `94.198.50.189` | POST `/api/v2/monitor/system/disconnect-admins/select` body `admins:[{id,method:ssh}]` header `X-CSRFTOKEN` **sin comillas** | HTTP 200 success. Token con comillas → 403 (no aplicado). Cuenta **no** deshabilitada | Tras POST: 3 sesiones `admin` HTTPS (ids 369090 / 370912 / 370829); 0 `support_fortinet`. WAN1/WAN2 link True 1G; port14 UP 1G; port11 link False; 6 AP connected + 1 discovered; 6 switch Connected + 1 Idle; 70 clientes Wi-Fi | N/A (sesión; la cuenta puede reconectar) | Cuenta intacta; SSH de esa IP cortado en ese instante |
| 2026-09-15 22:08 | — | Fase 0 | Reauth para continuar Fase 5 (quitar `ssh` de wan1/wan2 `allowaccess`) | Inspección Chrome VM | **STOP.** GUI = Login / 401. JSON `current-admins` en pestañas es **caché vieja**, no sesión viva. No se escribió usuario ni password | No PUT / no Save | No aplica | Fase 5 **no iniciada**. Esperando login `admin` en **este** Chrome |

Configuraciones modificadas (flash/CMDB): **0**  
Sesiones desconectadas: **CHG-003** (2× SSH `support_fortinet`)  
Equipos reiniciados: **0**  
Cuentas creadas/borradas/deshabilitadas: **0**  
Backup maestro: **CHG-001 completado** (archivo privado, no GitHub)  
CHG-002: **CANCELADO POR DECISIÓN OPERATIVA**  
CHG-004 (disable cuenta si reconecta): **no ejecutado** — falta GET fresco  
Fase 5 (quitar SSH WAN): **bloqueada** — sesión GUI caducada
