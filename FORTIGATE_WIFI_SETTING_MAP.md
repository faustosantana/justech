# Mapping Wi-Fi FortiOS 7.0.15 — FortiGate CAPITAL

GET-only desde dumps del 2026-09-15. **No POST/PUT en este archivo.**  
No reintentar el PUT `override-channel: 11` (entero) que devolvió HTTP 500.

Country actual: **US** (no cambiar a DO en esta sesión).

## Tabla

| SETTING | OBJECT | ENDPOINT / CLI PATH | CURRENT VALUE | CHANGE METHOD |
|---|---|---|---|---|
| Channel (profile default 2.4) | wtp-profile `FORALL` radio-1 | `GET/PUT /api/v2/cmdb/wireless-controller/wtp-profile/FORALL` · `radio-1.channel` | `1,6,11` · bonding **20 MHz** | PUT profile `radio-1.channel: [{chan:"1"},…]`. Afecta **todos** los AP FORALL sin override. No usar para un solo AP. |
| Channel (profile default 2.4) | wtp-profile `FAP221E-default` radio-1 | `…/wtp-profile/FAP221E-default` | `channel: []` (auto) · 20 MHz · darrp **disable** | Igual; APs 748/762/983 usan este perfil. Cambio de perfil = varios AP. |
| Channel (operativo) | monitor AP | `GET /api/v2/monitor/wifi/managed_ap` · `radio[].oper_chan` | A17:11 / AAH:6 / ACV:6 / 748:6 / 762:1 / 983:1 | Solo lectura. No hay PUT de oper_chan. |
| Channel (per-AP override) | wtp `FP221E…` radio-1/2 | `GET/PUT /api/v2/cmdb/wireless-controller/wtp/<WTPID>` · `radio-N.override-channel` + `radio-N.channel` | La mayoría **disable** + `channel []`. **AAH** ya `enable` (r1 1/6/11, r2 60/108/124) | Método correcto: `override-channel: "enable"` y `channel: [{chan:"11"}]`. **Prohibido** `override-channel: 11` (HTTP 500 en ACV; rollback 200). CLI: `config wireless-controller wtp` → `edit <id>` → `config radio-1` → `set override-channel enable` → `set channel 11`. |
| TX power | wtp-profile radio-1/2 | `radio-N.power-mode` / `power-level` / `power-value` | percentage, **level 100**, value 27 dBm en FORALL y FAP221E-default | PUT profile `power-level` (−3 ≈ bajar ~3 puntos de % no es 3 dB; en modo percentage bajar de 100→~50 es ~3 dB solo si el driver lo trata lineal — **medir RSSI**). Preferir per-AP. |
| TX power (per-AP) | wtp radio-N | `radio-N.override-txpower` + `power-level` | disable salvo **AAH r1 enable** @ 100 | PUT `override-txpower: enable` + `power-level`. No se aplicó. |
| Radio mode | wtp-profile radio-N | `radio-N.mode` / `band` | r1 `ap` 802.11n (FORALL) / `802.11n,g-only` (FAP221E-default); r2 `ap` 802.11ac; r3 disabled | PUT `mode`/`band`. No tocar en esta fase. |
| Background scan / DARRP | wtp-profile radio-N `darrp` | `…/wtp-profile/<name>` | **disable** en FORALL y FAP221E-default; **enable** en perfiles no usados FAP221 / FAP221C-default | PUT `darrp: enable` **puede retunar canales**. Global `wireless-controller setting.darrp-optimize` = 86400 s. **Pendiente / no aplicar** hasta poder limitar a un AP y tener rollback. No spectrum-analysis. |
| Channel utilization (monitor) | managed_ap / profile | monitor `radio[]` · profile `channel-utilization` | Monitor true en APs connected | GET only para decidir RF. |
| 802.11k (voice enterprise / RRM NR) | VAP/SSID | `GET/PUT /api/v2/cmdb/wireless-controller/vap/<name>` · `voice-enterprise` | **disable** en Empleados (`LaSociedad`), Gerencia (`LS`), Invitados (`LaSociedad_Guest`) | PUT `{ "voice-enterprise": "enable" }`. Un SSID primero (`Empleados`). No es el endpoint WTP. |
| 802.11v (neighbor report dual-band) | VAP/SSID | mismo VAP · `neighbor-report-dual-band` | **disable** en los 3 SSID | PUT `{ "neighbor-report-dual-band": "enable" }` junto con 11k. Validar AP/clientes antes de copiar a Gerencia/Invitados. |
| 802.11r (FT) | VAP/SSID | `fast-bss-transition` | **disable** en los 3 | **NO habilitar** esta sesión. |
| Fast roaming (legacy flag) | VAP | `fast-roaming` | **enable** (no es 11r) | No cambiar. |
| Sticky client | VAP | `sticky-client-remove` + thresholds | **disable**; 2g −79 / 5g −76 / 6g −76 | PUT VAP. No aplicado. |
| Frequency handoff | wtp-profile | `frequency-handoff` | **disable**; handoff-sta-thresh 55 (FORALL / FAP221E-default) | PUT profile. Afecta todos los AP del perfil. No aplicado. |
| WIDS / scan profile | wtp-profile radio `wids-profile` | `radio-N.wids-profile` | vacío en FORALL y FAP221E-default; `default` en FAP221 r1 | Asignar wids-profile es menos disruptivo que DARRP, pero no se validó el contenido de `default`. Pendiente. |

## AP → perfil (cmdb wtp)

| WTP ID | admin | profile | override 2.4 ch | override TX | oper 2.4 / 5 (monitor) |
|---|---|---|---|---|---|
| FP221E | discovered | FAP221E-default | disable | disable | connecting |
| FP221E5520099A17 | enable | FORALL | disable | disable | 11 / 149 |
| FP221E5520099AAH | enable | FORALL | **enable** 1/6/11 | r1 enable @100 | 6 / 124 |
| FP221E5520099ACV | enable | FORALL | disable (PUT 11 falló) | disable | 6 / 132 |
| FP221ETF22078748 | enable | FAP221E-default | disable | disable | 6 / 48 |
| FP221ETF22078762 | enable | FAP221E-default | disable | disable | 1 / 161 |
| FP221ETF22078983 | enable | FAP221E-default | disable | disable | 1 / 165 |

## Cómo evitar otro HTTP 500

1. **11k/v:** solo `PUT /api/v2/cmdb/wireless-controller/vap/Empleados` con strings `enable`. Distinto del WTP.  
2. **Canal por AP:** nunca mandar un número en `override-channel`. Usar `enable` + lista `{chan}`.  
3. **No PUT al perfil FORALL** para un experimento de un AP (mueve A17+AAH+ACV).  
4. Si 500: rollback inmediato del mismo objeto; no repetir el payload.
