# Registro de cambios — FortiGate CAPITAL

Ningún cambio de configuración se ha aplicado en el FortiGate.

| Fecha/hora UTC | CHANGE-ID | Autorización | Estado previo | Acción | Resultado | Pruebas | Rollback | Estado final |
|---|---|---|---|---|---|---|---|---|
| 2026-09-15 20:15 | — | Investigación forense READ-ONLY | 42 admin, sesión support_fortinet SSH activa | GET API / GUI logs | Completado; compromiso INCONCLUSO | Sesión admin HTTPS viva; 0 Apply/Save | No aplica | Sin cambios en el FortiGate |
| 2026-09-15 20:43 | CHG-001 | AUTORIZO CHG-001 ÚNICAMENTE | Sin backup maestro controlado; `current_config_unsaved=true` | GET `/api/v2/monitor/system/config/backup?scope=global` (sesión `admin`) | Backup privado 649162 bytes SHA-256 `8573a6e43632a5582c7bfab44aa339687b4ebbd4902742a45aaf1b8166e2f2e6` | Cabecera FG100E 7.0.15 build0632 hostname CAPITAL serial FG100ETK19012927; no HTML; no Save | No aplica (solo archivo local) | Equipo sin cambios; `.conf` fuera de git |
| 2026-09-15 21:13 | CHG-002 | CANCELADO POR DECISIÓN OPERATIVA | Usuario RO no creado | Ninguna | Cancelado; `admin` permanece cuenta operativa | No se pulsó Create/POST | No aplica | 0 cambios; no `justech_cursor_audit` |

Configuraciones modificadas: **0**  
Equipos reiniciados: **0**  
Cuentas creadas/borradas/deshabilitadas: **0**  
Backup maestro: **CHG-001 completado** (archivo privado, no GitHub)  
CHG-002: **CANCELADO POR DECISIÓN OPERATIVA** (no se creó `justech_cursor_audit`; no es un fallo técnico pendiente)
