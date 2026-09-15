# Auditoría Fortinet READ-ONLY — FortiGate CAPITAL

| Campo | Valor |
|---|---|
| Equipo | FortiGate 100E `CAPITAL` |
| Serial | FG100ETK19012927 |
| Destino auditado | `https://181.37.127.69/` (TCP/443) |
| FortiOS | v7.0.15 build0632 (GA, Mature) |
| Fecha de evidencia | 2026-09-15 ~18:12–18:45 UTC |
| Usuario de sesión | `admin` (perfil técnico `super_admin`) |
| Modo | **100% READ-ONLY** |
| Cambios autorizados / realizados | **NINGUNO / 0** |
| VDOM | `root` (único) |
| HA | **standalone** (no hay peer) |
| FortiAP gestionados | **SÍ** (6 online + 1 discovered) |
| FortiSwitch gestionados | **SÍ** (6 Connected + 1 Idle) |

**Problema reportado:** Wi-Fi lento, intermitente y con desconexiones; el proveedor de Internet “aparentemente no es la causa”.

**Conclusión resumida:** el ISP **no está descartado**. `wan1` (Tricom) tiene jitter ~42 ms y ~1 % de pérdida. Además hay un problema **RF real** (potencia máxima, co-channel 2.4 GHz, roaming incompleto, country US) y un problema **LAN** (FortiLink degradado a un solo 1 Gbps + rx-drops millonarios en uplinks). La percepción de “Wi-Fi malo” es la suma de esas tres capas.

No se muestran PSK, contraseñas, FortiToken, claves API ni private keys.

---

## 1. Informe ejecutivo (máx. 1 página)

Cliente: **Capital DBG** (`capitaldbg.com`). Sitio con FortiGate 100E, 6 FortiAP-221E y 7 FortiSwitch (1× 424E + 6× 224D-POE). ~80 clientes Wi-Fi al momento de la muestra; pico 5 GHz en 24 h: **116**.

| Área | Estado | Lectura para dirección / TI |
|---|---|---|
| WAN / ISP | 🟠 Importante | Tricom (`wan1`) **sí** degrada: jitter 42 ms y 1 % loss. Liberty (`wan2`) está sano. El firewall reparte 50/50 **sin SLA**, así que parte del tráfico usa el enlace malo. |
| Wi-Fi RF | 🔴 Crítico para la queja | Potencia 100 % (~27 dBm), 3 AP en canal 6 y 2 en canal 1, country **US** en República Dominicana, 802.11r/k/v incompletos, sticky clients. |
| LAN / FortiLink | 🟠 Importante | Agregado FortiLink **roto** (solo `port14` UP). Uplinks de switch con **millones** de drops. Los AP sí están a 1 Gbps full-duplex. |
| Seguridad | 🔴 Crítico | HTTPS+SSH en Internet, **42** super_admin, MFA en 2/42, SSL-VPN en `any`, políticas `ssl.root` → `any`. Sesión SSH `support_fortinet` desde `94.198.50.189`. |
| Licencias / logs | 🟠 Importante | UTM FortiGuard **expirado 2026-08-20**. Sin disco de logs (API de eventos 404): no hay historia fina de cortes. |
| DHCP/DNS | 🟡 Atención | Lease 7 días (181 leases en Empleados). Clientes Wi-Fi solo con DNS `8.8.8.8`. |
| Firmware | 🟡 Atención | FS224D en **3.6.11 (2019)** vs FortiOS 7.0.15 vs un 424E en 7.4.2. |

**Causa raíz más probable de la lentitud:** (1) RF: celdas demasiado potentes + CCI 2.4 + AP de Piso 1 con 31 clientes; (2) SD-WAN 50/50 hacia `wan1` con jitter; (3) drops en uplinks FortiLink de 1 Gbps.

**Causa raíz más probable de la intermitencia/desconexiones:** roaming deficiente (sin 11r/11k efectivo) + sticky clients + posibles eventos DFS (canales 124/132) + rejoin CAPWAP masivo el 2026-09-04 + FortiLink SPOF.

**No se corrigió nada.** Cualquier cambio requiere autorización explícita y, en RF/FortiLink/WAN, ventana de mantenimiento.

---

## 2. Control de cambios de esta auditoría

| Ítem | Valor |
|---|---|
| Configuraciones modificadas | **0** |
| Equipos reiniciados | **0** |
| Cambios de firewall | **0** |
| Cambios Wi-Fi | **0** |
| Cambios DHCP/DNS | **0** |
| Cambios FortiSwitch | **0** |
| Cambios FortiAP | **0** |
| Cambios de firmware | **0** |
| Credenciales almacenadas | **0** |
| API keys creadas | **0** |
| Trusted Hosts modificados | **0** |

**Nota de proceso:** un subproceso de recolección intentó abrir rutas `/api/v2/...` cuando la sesión web caducó y FortiGate interpretó esa ruta como usuario, generando *Too many login failures*. **No se creó ningún usuario ni se usó una contraseña inventada.** A partir de esa alerta no se reintentó autenticación automática.

---

## 3. Fase 1 — Identificación del entorno

### FortiGate

| Atributo | Valor | Evidencia |
|---|---|---|
| Hostname | CAPITAL | `monitor/system/status` |
| Modelo | FortiGate 100E (`FG100E`) | idem |
| Serial | FG100ETK19012927 | cabecera API `serial` |
| FortiOS | v7.0.15 build 632, GA, Mature | `monitor/system/firmware` |
| VDOM | root únicamente | `cmdb/system/vdom` |
| HA | standalone; peer vacío | `cmdb/system/ha` `mode=standalone`; `ha-peer=[]` |
| Wireless controller | enable | `system.global` |
| Switch controller | enable | `system.global` |
| Timezone | índice `15` (AST, típico Caribe) + DST enable | `system.global` |
| NTP | FortiGuard, `ntpsync=enable`; NTP server-mode en `fortilink` | `cmdb/system/ntp` |
| DNS FortiGate | 96.45.45.45 / 96.45.46.46 **DoT** `globalsdns.fortinet.net`; dominio `capitaldbg.com` | `cmdb/system/dns` |
| Admin ports | HTTPS 443, SSH 22, Telnet 23 (telnet no verificado en WAN) | `system.global` |
| Log disk | **not_available** | `system/status` |
| CPU muestra | ~18 % actual; 1-min avg 15 % max 29 %; un core 38 % system | `performance/status` + resource usage |
| RAM | 46 % de ~3.0 GiB (used 1.48 GiB / total 3.19 GiB) | performance |
| Conserved mode | **NO VERIFICADO** (no aparece en el payload) | — |
| Temperatura / sensores | **NO VERIFICADO** (`sensor-info` 404) | — |
| Sesiones | ~1970–1980 por WAN en SD-WAN members; capacidad máxima **NO VERIFICADA** (API session/summary 404) | SD-WAN members |
| FortiCare | registered; cuenta `fausto@capitaldbg.com`; company Capital DBG | license/status |
| UTM FortiGuard | **expired 2026-08-20** AV/IPS/AppCtrl/WebFilter/Antispam | license/status |
| IPS DB | última actualización **2024-09-16** | license/status |
| FortiCloud logging | free_license | license/status |
| Uptime FortiGate | **NO VERIFICADO** (no vino en status) | — |

Administradores conectados durante la muestra 2:

- `admin` / HTTPS / `wan1` (sesión de esta auditoría).
- `support_fortinet` / SSH / `wan1` **y** `wan2` / origen `94.198.50.189` (persistente).

### Inventario FortiAP

Firmware común online: `FP221E-v7.0-build0115`. Uplink observado: **1000 Mbps full-duplex** (ningún AP a 100 Mbps). CAPWAP vía interfaz `Vlan30`. Rejoin CAPWAP: 2026-09-04 07:49. Last reboot AP: 2026-07-23 07:08.

| Nombre / serial | IP | MAC | Estado | Clientes | Perfil | Switch / puerto (LLDP) |
|---|---|---|---|---|---|---|
| FP221E (placeholder) | 0.0.0.0 | 00:00:00:00:00:00 | connecting / discovered | 0 | FAP221E-default | — |
| FP221E5520099A17 | 10.20.40.33 | e0:23:ff:c4:7c:b8 | connected | 13 | FORALL | FS224D3Z14001698 / port9 |
| FP221E5520099AAH | 10.20.40.26 | e0:23:ff:c4:9a:58 | connected | 16 | FORALL | FS224D3Z14001687 / port2 |
| FP221E5520099ACV | 10.20.40.242 | e0:23:ff:c4:a1:d8 | connected | 2 | FORALL | FS224D3Z14000932 / port2 |
| FP221ETF22078748 | 10.20.40.50 | 84:39:8f:23:75:18 | connected | 6 | FAP221E-default | FS224D3Z14001698 / port11 |
| FP221ETF22078762 | 10.20.40.32 | 84:39:8f:23:76:68 | connected | 12 | FAP221E-default | FS224D3Z14001687 / port4 |
| FP221ETF22078983 | 10.20.40.30 | 84:39:8f:23:8b:20 | connected | 31 | FAP221E-default | **LLDP vacío** (loc=`Piso 1`) |

6 GHz: **NO APLICA** (FAP-221E = Wi-Fi 5).

### Inventario FortiSwitch

| Serial | Firmware | Estado | PoE budget | IP FortiLink | Join |
|---|---|---|---|---|---|
| S424ENTF20000399 | S424EN-v7.4.2-build801 (2023-12-07) | Connected | 0 (no PoE en este modelo/role) | 169.254.2.3 | 2026-07-23 07:10 |
| FS224D3Z14001985 | FS224D-v3.6.11-build432 (2019-11-08) | Connected | 180 W | 169.254.2.4 | 2026-07-23 07:10 |
| FS224D3Z14002019 | 3.6.11 | Connected | 180 W | 169.254.2.5 | 2026-07-23 07:10 |
| FS224D3Z14001687 | 3.6.11 | Connected | 180 W | 169.254.2.2 | 2026-07-23 07:10 |
| FS224D3Z14000932 | 3.6.11 | Connected | 180 W | 169.254.2.6 | 2026-07-23 07:11 |
| FS224D3Z14001698 | 3.6.11 | Connected | 180 W | 169.254.2.7 | 2026-07-23 07:10 |
| FS224D3Z15000948 | (vacío) | **Idle** | 0 | — | — |

FortiLink en FortiGate: aggregate `port11` + `port14`, IP `169.254.2.1/24`. En operación **solo `port14` tiene link 1 Gbps**; `port11` está down.

---

## 4. Fase 2 — Salud del FortiGate

**CPU:** utilización puntual ~18 % (user 3 + system 12, idle 82). Core 2 con 38 % system: no es saturación global, pero hay trabajo de plano de control/datapath en un núcleo. Histórico 1 min: min 7 / avg 15 / max 29. **Procesos (WAD, IPS, miglogd): NO VERIFICADO** (no se ejecutó `diagnose sys top` para no cargar el equipo).

**RAM:** ~46 %. Libre ~1.39 GiB + freeable ~317 MiB. No hay evidencia de conserve mode.

**Sesiones:** ~1970 por miembro SD-WAN en el instante. Setup rate: **NO VERIFICADO**.

**Interfaces físicas relevantes (monitor, errores 0):**

| Interfaz | Alias | Link | Speed | Duplex | RX/TX errors | Notas |
|---|---|---|---|---|---|---|
| wan1 | Tricom | UP | 1000 | full | 0 / 0 | Admin HTTPS/SSH |
| wan2 | Liberty-Netowkr | UP | 1000 | full | 0 / 0 | Admin HTTPS/SSH/fabric |
| port14 | FortiLink miembro | UP | 1000 | full | 0 / 0 | Alto volumen (~9.8 TB TX acumulado) |
| port11 | FortiLink miembro | **DOWN** | — | — | — | LAG degradado |
| port15 | — | UP | **100** | full | 0 | Casi sin tráfico |
| port10 | — | UP | 1000 | full | 0 | Tráfico residual |
| mgmt | 192.168.0.99 | DOWN (sin cable) | — | — | — | HTTPS/SSH/HTTP/fgfm |
| dmz | 172.16.0.1 | DOWN | — | — | — | |
| ha1/ha2 | — | DOWN | — | — | — | HA no usada |
| port1/2/3 | Piso_1/2/3 | DOWN en monitor | — | — | — | Configurados con IP/DHCP; sin link actual |

No hay CRC en el FortiGate. El problema físico más claro en el FG es **FortiLink de un solo miembro**.

---

## 5. Fase 3 — WAN e Internet

| | wan1 Tricom | wan2 Liberty |
|---|---|---|
| IP / máscara | 181.37.127.69/24 | 179.51.67.67/31 |
| Gateway | 181.37.127.1 | 179.51.67.66 |
| Link | 1 Gbps full, 0 errores | 1 Gbps full, 0 errores |
| SD-WAN zona | upg-zone-wan1 | upg-zone-wan2 |
| Weight / priority | 50 / 1 | 50 / 1 |
| Latency (ping 8.8.8.8) | **56.0 ms** | 26.2 ms |
| Jitter | **42.4 ms** | **0.29 ms** |
| Packet loss | **1 %** | **0 %** |
| TX / RX bandwidth muestra | 2.8 / 16.9 Mbps | 2.5 / 18.9 Mbps |
| state_changed (epoch) | 1789400447 (~2026-09-14 15:40 UTC) | 1789276086 (~2026-09-13 05:08 UTC) |

Health-check `TRICOM_HC`: probe ping a `"8.8.8.8" "8.8.8.8"`, interval 500 ms, **sla=[]**, umbrales de loss/latency/jitter en 0 (no disparan failover por calidad). `service` SD-WAN vacío → no hay reglas de aplicación; el default es weight-based 50/50.

Rutas 0.0.0.0/0: ambas WAN distance 1 priority 1.

**ISP = PROBLEMA PARCIAL (wan1 SÍ / wan2 NO).**

Evidencia: jitter 42 ms y 1 % loss en Tricom frente a Liberty limpio, **sin** errores de capa 2. Eso no explica todo el Wi-Fi local, pero **tampoco permite descartar al ISP**.

---

## 6. Fase 4 — FortiSwitch / LAN / FortiLink

- FortiLink: aggregate 802.3ad declarado con 2 miembros; **operación 1/2**.
- STP/RSTP detallado: **NO VERIFICADO** (no se volcó `stp` por puerto).
- Native VLAN en ISL: `vsw.fortilink` (VLAN 1 de FortiLink). APs en **Vlan30**.
- PoE: budget 180 W en cada 224D; APs alimentados (están online a 1G). `ap_poe_mode=invalid` en API de AP es campo poco fiable; LLDP muestra 1000BaseTFD. Consumo PoE exacto: **NO VERIFICADO** (endpoint poe-status 404).
- Loops: no hay evidencia directa; **NO VERIFICADO**.
- CRC-alignments en stats de switch: **0** en los puertos revisados.
- **rx-drops altos** en uplinks `port23` (ISL): 2 022 608 y 1 436 738 en dos 224D. Eso es congestión/descarte, no CRC.
- Muchos access ports a **100 Mbps** (teléfonos/PCs/cable). **Los AP están a 1000 full**; no hay AP a 100 Mbps.
- Switch Idle `FS224D3Z15000948`: fuera de servicio.

---

## 7. Fases 5–8 — Wi-Fi profundo, clientes, roaming, SSID

### Matriz RF (20 MHz en perfiles; potencia 100 %)

| AP | 2.4 ch / util / tx | 5 ch / util / tx | Clientes | Notas |
|---|---|---|---|---|
| 99A17 | 11 / 18 % / 27 dBm | 149 / 10 % / 28 dBm | 13 | FORALL |
| 99AAH | **6** / 34 % / 27 | **124 DFS** / 25 % / 20 | 16 | override canal/potencia |
| 99ACV | **6** / 21 % / 27 | **132 DFS** / 1 % / 20 | 2 | |
| 78748 | **6** / 29 % / 27 | 48 / 2 % / 29 | 6 | g-only en 2.4; country_code poor |
| 78762 | **1** / 38 % / 27 | 161 / 6 % / 29 | 12 | g-only |
| 78983 Piso1 | **1** / 18 % / 27 | **165** / 7 % / 24 | **31** | sin LLDP |

**Co-channel 2.4:** canal 6 ×3, canal 1 ×2, canal 11 ×1. Adjacent-channel 2.4 (usar 1+6+11 a 20 MHz no es ACI clásico si son solo 1/6/11; el daño es **CCI** por reutilizar 1 y 6 con potencia de “torre”).

**5 GHz:** 20 MHz en perfil (no hay exceso de 80 MHz configurado). Canales 48, 124, 132, 149, 161, 165. DFS en 124/132.

**Interferencia reportada por el WLC:** 0 (scans deshabilitados) → el “health good” **no es fiable**.

### SSID (PSK enmascarada)

| VAP | SSID | Seguridad | Modo | VLAN/subnet | Roaming | Isolation |
|---|---|---|---|---|---|---|
| Empleados | LaSociedad | WPA2-only-Personal AES | tunnel | 10.10.11.0/24 | fast-roaming enable; **FT/11r disable**; OKC enable; 11k neighbor disable; 11v disable; sticky-remove **disable** | intra-vap-privacy **disable** |
| Gerencia | LS | igual | tunnel | 10.10.10.0/24 | igual | disable |
| Invitados | LaSociedad_Guest | igual | tunnel | 10.10.13.0/24 | igual | disable (invitados se ven entre sí) |

PMF disable. Captive portal no activo (portal-type auth pero local-bridging disable, sin evidencia de portal en clientes). Band steering (`frequency-handoff`) **disable**. `country=US`.

Clientes asociados: LaSociedad 73, Guest 7, LS 0 en la muestra.

### Clientes (n=80)

| Clase RSSI | Criterio | n | % |
|---|---|---|---|
| Excelente | ≥ −55 dBm | 23 | 28.8 % |
| Bueno | −56 a −65 | 35 | 43.8 % |
| Aceptable | −66 a −70 | 12 | 15.0 % |
| Malo | −71 a −80 | 9 | 11.3 % |
| Crítico | < −80 | 1 | 1.3 % |

Banda: **74 en 5 GHz (92.5 %), 6 en 2.4 GHz (7.5 %)**. Band steering “de facto” por clientes, no por política.

802.11k capable 7/80, 11v 9/80, 11r **0/80** (coherente con FT disable).

**Cliente crítico:** MAC `2e:ca:5e:93:f2:9d` / 10.10.11.46 / AP 99AAH / ch 124 / RSSI **−87** / SNR **8** / discards 6 % → sticky o cobertura borde.

Otros débiles (≤ −74 dBm): `5e:04:be:6a:ef:55` (−76), `6e:12:ef:00:62:65` (−76), `78:20:a5:f3:2b:09` Nintendo 2.4 (−77), varios −71 en 78748/78983.

Retries % en clientes: API reportó 0 en casi todos (el contador de radio `tx_retries_percent=0` tampoco es creíble frente a millones de `mac_errors_tx`). Tratar retries de cliente como **NO VERIFICADO / poco fiable**.

---

## 8. Fase 9 — DHCP

19 scopes. Wi-Fi:

- Empleados `10.10.11.10–254`, lease **604800 s (7 días)**, DNS `8.8.8.8` only, gw 10.10.11.1. **181 leases**.
- Invitados `10.10.13.2–254`, 7 días, DNS 8.8.8.8. **88 leases**.
- Gerencia `10.10.10.2–254`, 7 días, 8.8.8.8. **2 leases**.
- Vlan30 (APs) `10.20.40.20–254`, 7 días, 8.8.8.8. **38 leases**.

Total leases sistema: **324**. No se vio scope al 100 %, pero Empleados al **~74 %** con lease de una semana es riesgo de agotamiento por dispositivos que ya no están. Pico 5 GHz 24 h = 116: todavía cabe, pero el margen se come con BYOD + leases zombis.

Conflictos DHCP: **NO VERIFICADO** (sin logs).

---

## 9. Fase 10 — DNS

- FortiGate: FortiGuard DoT (bien para el propio FG).
- Clientes Wi-Fi: **solo 8.8.8.8**, sin secundario, sin usar el DNS del FortiGate.
- Latencia DNS medida: **NO VERIFICADA** (no se lanzó dig/nslookup masivo).
- Relación con “Internet lento”: **probable factor contribuyente** cuando SD-WAN manda el flujo a wan1 (8.8.8.8 es además el probe).

---

## 10. Fase 11 — Firewall / NAT / UTM

27 políticas. NAT hacia Internet en EMPLEADOS-LLB, GERENCIA-LLB, GUEST-LLB, GERENCIA PISO 3.

| ID | Nombre | Hits | Riesgo |
|---|---|---|---|
| 47 | EMPLEADOS-LLB Empleados→wan1+wan2 ALL NAT | 27 591 369 | UTM enable pero AV/IPS/web vacíos; ssl profile `Hola` |
| 48 | GUEST-LLB | 8 950 337 | certificate-inspection + app/web default |
| 53 | GERENCIA PISO 3 | 6 586 883 | sin UTM |
| 24 | Guest-to-All ssl.root→any ALL | 1 947 484 | **any/any, log disable** |
| 60 | `` ` `` ssl.root→any ALL | 139 442 | nombre basura; any/any; log disable |
| 27 | WIFI-TO-VLAN empleados→Vlan30/Piso2 ALL | 81 578 | inter-VLAN amplio |

Inspección SSL full: no. Certificate-inspection en guest e inbound histórico. Licencias UTM vencidas → IPS/AV no actualizan aunque se asignen.

Shadowing fino: **NO VERIFICADO** al 100 %; las dos ssl.root any/any son las más peligrosas.

---

## 11. Fase 12 — Seguridad

- Administración desde WAN: **SÍ** (HTTPS+SSH+PING en wan1 y wan2).
- Trusted Hosts: **ninguno efectivo** (0.0.0.0/0).
- MFA: solo `admin` y `justech`.
- Cuentas: 42 super_admin (AdminLocalTechF0rti, Forti_Support, IT-SUPPORT, IT_Admin, Soporte, admin, admin2, fortinet-*, fsantana, justech, ldap, oldadmin, support_fortinet, vpnforti_sup, etc.).
- SSL-VPN: enable, puerto **19543**, source-interface **any**, TLS1.1 mínimo, timeout 0, cert factory.
- HTTP en Vlan30, vlan50, vlan10/20, mgmt.
- SNMP: **NO VERIFICADO** en detalle (sysinfo no volcado).
- Certificado admin: autofirmado Fortinet CN=FortiGate.

---

## 12. Fase 13 — Logs

- Disco: no disponible.
- `GET /api/v2/log/memory/event` y `log/disk/*`: **404**.
- `monitor/log/stats`: hay contadores de traffic/event/webfilter/app-ctrl/ssl (p. ej. event ~13k–51k según bucket).
- Correlación de AP reboot, DFS, DHCP fail, FortiLink down: **NO VERIFICADA** por ausencia de log detallado.
- Evidencia indirecta de evento masivo: CAPWAP join simultáneo 2026-09-04 07:49.

---

## 13. Fase 14 — Firmware y compatibilidad

| Componente | Versión | Comentario |
|---|---|---|
| FortiGate 100E | 7.0.15 / 632 Mature | Tren 7.0 antiguo respecto a 7.4/7.6; aún GA Mature |
| FAP-221E | 7.0 build 0115 | Viejo dentro de 7.0; no 7.2/7.4 AP image |
| FS224D-POE | **3.6.11 (2019)** | EOS práctico; riesgo alto con FortiOS 7.0 |
| FS424E | 7.4.2 | Más nuevo que el propio FortiGate (7.0.15) → matriz desigual |

**NO se actualizó nada.**

---

## 14. Correlación de causa raíz

### A. Lentitud Wi-Fi

| Tipo | Qué |
|---|---|
| **Causa** | Airtime 2.4 destruido por CCI + potencia 27 dBm; AP Piso 1 con 31 clientes; uplinks switch descartando; parte del Internet sale por wan1 con jitter 42 ms |
| **Síntoma** | “El Wi-Fi está lento” / páginas que tardan |
| **Factor** | Tunnel mode (todo pasa por FG+FortiLink 1G); DNS único 8.8.8.8; UTM/SSL profile `Hola`; leases DHCP largos no explican lentitud sostenida |

### B. Intermitencia

| Tipo | Qué |
|---|---|
| **Causa** | Roaming incompleto + sticky (RSSI −87) + DFS 124/132 + FortiLink SPOF + wan1 1 % loss |
| **Síntoma** | Va y viene; Zoom/Teams se corta |
| **Factor** | Health AP “good” porque no hay scan de interferencia |

### C. Desconexiones

| Tipo | Qué |
|---|---|
| **Causa** | Reauth WPA2 sin 11r; posible radar DFS; evento CAPWAP 4-sep; DHCP 7 días como causa secundaria al asociar de nuevo |
| **Síntoma** | “Se cayó el Wi-Fi” |
| **Factor** | idle timeout cliente 300 s (timers) — normal, no agresivo |

### D. Bajo rendimiento

Suma de A + WAN1 + drops ISL. Los AP **no** están a 100 Mbps.

### E. Por zona

- **Piso 1 (78983):** 31 clientes, ch 165, sin LLDP (ubicación/cableado dudoso).
- **AAH:** override + DFS 124 + cliente −87 dBm.
- **78762/78748:** perfil default g-only, ch 1 y 6.

---

## 15. Preguntas obligatorias

1. ¿El ISP parece ser el problema? **SÍ (parcial, wan1)** — jitter 42 ms y 1 % loss vs wan2 sano.  
2. ¿Pérdida de paquetes WAN? **SÍ** en wan1 (1 %); **NO** en wan2; **NO** errores L2.  
3. ¿Jitter anormal? **SÍ** wan1 42 ms; **NO** wan2 0.29 ms.  
4. ¿LAN con errores? **SÍ (drops, no CRC)** en ISL; CRC **NO** visto.  
5. ¿Wi-Fi con problemas? **SÍ**.  
6. ¿Saturación? **SÍ relativa** (Piso 1 31 clientes; util 2.4 hasta 38 %; ISL drops).  
7. ¿Interferencia? **SÍ inferida** (CCI); scanner **NO** habilitado.  
8. ¿Co-channel? **SÍ** 2.4 ch 1 y 6.  
9. ¿Adjacent-channel? **NO** en 2.4 (solo 1/6/11 a 20 MHz). 5 GHz no ACI grave a 20 MHz.  
10. ¿Mala planificación de canales? **SÍ**.  
11. ¿Potencia correcta? **NO** (100 % / 27–29 dBm).  
12. ¿AP bien distribuidos? **NO VERIFICADO** físicamente; Piso 1 desbalanceado y un AP sin LLDP.  
13. ¿Uplinks de AP lentos? **NO** (1000 full). FortiLink de sitio **SÍ** (1G único).  
14. ¿AP a 100 Mbps? **NO**. Puertos de usuario **SÍ** varios a 100.  
15. ¿CRC? **NO** en FG ni en stats switch (0 crc-alignments).  
16. ¿PoE? **NO VERIFICADO** consumo; APs online ⇒ PoE suficiente en los 6 vivos. Switch Idle posible PoE/cable.  
17. ¿Clientes señal deficiente? **SÍ** 10/80 malo+crítico.  
18. ¿Sticky? **SÍ** (ejemplo −87 dBm; sticky-remove disable).  
19. ¿Roaming problemático? **SÍ** (sin FT/11k efectivo).  
20. ¿802.11k/v/r correcto? **NO**.  
21. ¿DHCP? **SÍ riesgo** (7 días, 181 leases); no se demostró pool empty ahora.  
22. ¿DNS? **SÍ factor** (solo 8.8.8.8 + wan1 mala).  
23. ¿Cuellos de botella? **SÍ** FortiLink 1G, ISL drops, AP Piso 1, wan1.  
24. ¿AP saturado? **SÍ relativo** Piso 1.  
25. ¿Seguridad peligrosa? **SÍ**.  
26. ¿Admin expuesto innecesariamente? **SÍ**.  
27. ¿Firmware viejo/problemático? **SÍ** FS224D 3.6.11 y AP 7.0-0115; FG 7.0.15 maduro pero tren viejo.  
28. ¿Causa más probable intermitencia? **Roaming/sticky/DFS + FortiLink SPOF + wan1 loss** (combinada).  
29. ¿Causa más probable lentitud? **RF (potencia/CCI/load) + wan1 jitter + drops ISL**.

---

## 16. Top 10 problemas (impacto)

1. **Admin y SSL-VPN en Internet + 42 super_admin** — evidencia allowaccess WAN y ssl.root any/any — impacto compromiso total — P0 — recortar exposición.  
2. **Sesión SSH support_fortinet 94.198.50.189** — current-admins — impacto acceso persistente — P0 — validar o cortar.  
3. **Potencia 100 % + CCI 2.4 (ch 6×3, ch 1×2)** — radios — impacto Wi-Fi lento/inestable — P1 — plan de canales y bajar dBm.  
4. **Roaming 11k/v/r incompleto y sticky-remove off** — VAP/WTP — impacto cortes al moverse — P1 — habilitar k/v, sticky.  
5. **Country US + DFS 124/132** — setting/radios — impacto caídas por radar/regulación — P1 — country DO, evitar DFS.  
6. **FortiLink port11 down + rx-drops millonarios** — monitor IF/switch — impacto pérdida LAN que se siente Wi-Fi — P1 — restaurar LAG.  
7. **wan1 jitter 42 ms / 1 % loss + SD-WAN 50/50 sin SLA** — health-check — impacto Internet a tirones — P1 — SLA y preferir wan2.  
8. **FortiGuard UTM expirado** — license — impacto seguridad ciega — P1 — renovar.  
9. **FS224D 3.6.11 (2019) vs FG 7.0.15 / 424E 7.4.2** — firmware — impacto bugs FortiLink/Wi-Fi — P2 — plan upgrade.  
10. **DHCP 7 días + DNS solo 8.8.8.8** — dhcp server — impacto asociación/navegación — P2 — lease corto y DNS dual.

---

## 17. Hallazgos (formato ID)

Ver `FORTIGATE_FINDINGS.csv` (35 filas: SEC, WAN, WIFI, NET, DHCP, SYS, FW). Cada uno sigue evidencia → diagnóstico → impacto → recomendación, con cambio/ventana/rollback.

---

## 18. Plan de corrección (NO ejecutado)

### P0 — Crítico (seguridad, no “acelera el Wi-Fi” pero es urgente)

| Acción | Evidencia | Riesgo al aplicar | Rollback | Ventana | Prueba |
|---|---|---|---|---|---|
| Confirmar si `94.198.50.189` / `support_fortinet` es soporte real; si no, cortar SSH y rotar | current-admins | Cortar soporte legítimo | Reabrir sesión autorizada | No (si es abuso) | `current-admins` vacío de esa IP |
| Quitar HTTPS/SSH de wan1/wan2; admin solo por VPN/mgmt | allowaccess | Quedarse fuera si VPN mal | Restaurar allowaccess | Sí | Login interno OK, WAN timeout |
| Restringir SSL-VPN (`any` → interfaces internas) y políticas 24/60 | ssl settings + policy | Usuarios VPN remotos caen | Revertir policies | Sí | Portal no en 0.0.0.0; usuarios de prueba |

### P1 — Alto (estabilidad Wi-Fi / WAN / LAN)

| Acción | Por qué | Riesgo | Ventana |
|---|---|---|---|
| Country `DO`, replantear canales 2.4 1/6/11 únicos, 5 GHz no DFS, bajar potencia | WIFI-001/002/004/005 | Cobertura agujeros | Sí, fuera de horario |
| Unificar perfil AP; quitar g-only; enable background scan; sticky-remove; frequency-handoff | WIFI-006/007/010 | Clientes antiguos 2.4 | Sí |
| Enable 11k/11v; 11r solo tras prueba PSK | WIFI-003 | Algunos clientes no roaman bien | Sí, piloto 1 SSID |
| Restaurar FortiLink `port11` | NET-001/002 | Microcorte LAG | Sí |
| SD-WAN SLA (loss 2 %, latency 80 ms, jitter 15 ms) preferir wan2; abrir ticket Tricom | WAN-001/002 | Failover inesperado | Sí, baja |
| Renovar FortiGuard | SEC-006 | Ninguno | No |

### P2 — Medio

Lease DHCP 4–8 h; DNS 8.8.8.8 + 1.1.1.1 o FortiGate; isolation guest; recortar cuentas admin; syslog/FAZ; investigar switch Idle; puertos 100 Mbps.

### P3 — Optimización

Airtime fairness; ATF; upgrade controlado FG 7.0 → 7.4 alineando AP/switch; HA si hay presupuesto; quitar SSID LS del aire si no hay clientes; local-bridge vs tunnel según diseño.

Cada acción: **rollback = backup config + nota de cambio**. Prueba posterior: muestreo de clientes RSSI, health-check SD-WAN, `port11` UP, 0 drops nuevos, test roaming Piso 1.

---

## 19. Matrices (archivos)

- `FORTIGATE_AP_MATRIX.csv`
- `FORTIGATE_WIFI_CLIENTS.csv` (80 clientes; sin PSK)
- `FORTIGATE_SWITCH_PORTS.csv`
- `FORTIGATE_INVENTORY.csv`
- `FORTIGATE_FINDINGS.csv`

---

## 20. Limitaciones (NO VERIFICADO)

- Logs event/wireless detallados (API 404, sin disk).
- `diagnose sys top` / procesos WAD-IPS (no ejecutado a propósito).
- Spectrum analysis (disruptivo; no lanzado).
- PoE watts por puerto.
- STP event history.
- Medición iperf/speedtest de usuario final.
- Validación legal de country DO vs US en campo.
- Identidad real de `94.198.50.189`.

---

## 21. Cierre

Auditoría READ-ONLY completada sobre sesión HTTPS autenticada por el propietario. **Ninguna corrección aplicada.**

Siguiente paso: autorización explícita por ítem P0/P1. Prioridad de negocio sugerida: (1) validar SSH externo, (2) RF+FortiLink+SD-WAN SLA, (3) higiene de cuentas y cierre de admin WAN.
