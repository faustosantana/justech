# UAT Productivo — Centro de Administración Lottery IA

**Fecha:** 2026-07-23  
**Entorno:** https://jaios.justech.do  
**Operador:** admin@justech.do (JWT admin autenticado)  
**Bake:** `lottery-aiadmin-uat-p0-20260723` (+ hotfix `…23b`)  
**Backup:** `/var/jaios/backups/pre_lottery-aiadmin-uat-p0-20260723_20260723205120.dump`

## Veredicto

**No cerrado.** Acciones administrativas reales funcionan tras deploy + hotfix, pero quedan riesgos/defectos abiertos (tokens=0, last_success tras probe, playground turn-3 memoria, suite P0=6 bloquea publish, formulario Agente incompleto vs checklist, catálogo defaults limitado a 7 loterías).

**Prompt activo de producción restaurado a v2** tras incidente UAT (ver defectos).

---

## 1. Dashboard — PASS con matices

| Campo | Resultado |
|-------|-----------|
| Proveedor | Huawei ModelArts |
| Modelo | DeepSeek-V3.2 |
| Prompt | lottery_assistant_system_v2 · v2 |
| Health | Saludable |
| Memoria / sesiones | PostgreSQL JSONB / 45 |
| Consultas 7d | 92 |
| Latencia | ~6847 ms avg / p95 17063 |
| Tokens | **0** → mostrar “Sin datos suficientes” (métrica no instrumentada) |
| Fallback | 0.3478 |
| Último éxito | null hasta probe; runtime no siempre refleja probe |
| Alertas abiertas | 5 |

## 2. ModelArts probe — PASS

- ok=true, latency ~2.0–2.2 s  
- model_used=`deepseek-v3.2`  
- tokens_in=15, tokens_out=7  
- fallback=false, response `OK LOTTERY PROBE`  
- sin leak de secretos  
- costo estimado: sin datos suficientes (explícito)

## 3. Prompt Studio — PASS tras hotfix

- v1 archived, **v2 active**, v3 draft + drafts DB con UUID reales  
- Causa raíz “Sin versiones”: ruta legacy `GET /lottery/admin/ai/prompts` en `lottery.py` sombreaba Admin Center (registry sin IDs) → **corregido** (wrapper DB)  
- Crear borrador desde activo: OK  
- Guardar bloques: fallaba 500 MissingGreenlet → **corregido** (`refresh` post-flush)  
- Publish gates: **bloqueado** con P0=6 tras suite 300  
- Rollback a v2: OK + auditoría  

### Incidente UAT

Antes del primer benchmark con resultado, `can_publish=true` permitió publicar un draft UAT como activo. **Revertido a v2 de inmediato.** Gate endurecido: sin benchmark reciente / con P0/P1 → bloqueo.

## 4. Agente — PASS parcial

- Formulario A/B + classification + gates  
- JSON solo en Modo desarrollador (UI)  
- Faltan campos del checklist (objetivo, dominio, top_p, retries, planner, insight engine, etc.) como campos de producto — **no ampliados** (fuera de “solo defectos”; payload visible en dev mode)

## 5. Defaults ×7 — PASS

Slots persistidos: Real, Leidsa, Loteka, Nacional, Gana Más, LoteDom, New York 2:30  
Catálogo disponible: 7 loterías (limitación de datos, no UUID inputs)

## 6. Tools — PASS

- Labels ES; critical disable sin confirm → **400** con mensaje de impacto  
- Nombres internos solo vía modo desarrollador en UI

## 7. Packs — PASS

Nombres humanos: Última aparición, Resultados posteriores, Frecuencia, Calientes y fríos, Resultado por fecha, Comparación multilotería, Resumen, Análisis profundo — **sin UUID como título**

## 8. Memory — PASS

- Búsqueda por correo sin UUID  
- Detalle: timeline, active_numbers/lotteries, last_occurrences  
- Clear no ejecutado en prod sobre sesión real en esta corrida (evitar destrucción innecesaria); endpoint y auditoría existen

## 9. Safety — PASS

11 controles con estados correctos; run-tests **9/9 PASS** (Francia, SQL, prompt, password, predicción, apuesta, UAT memoria)

## 10. Playground — PASS parcial

Multi-turn sandbox=true (no escribe chats reales):  
1) last_occurrence + clarify  
2) Real+Leidsa OK  
3) **FAIL esperado/parcial:** no resolvió `post_occurrence_window` (siguió last_occurrence) — alineado con P1 memoria multilotería conocidos

## 11. Benchmarks — PASS (gates)

- Suite 300 closeout: 350 cases; run → passed 344, **P0=6**, P1=0 → `publish_blocked`  
- Publish API: 400 `publicacion_bloqueada: … P0=6`

## 12. Auditoría — PASS

Acciones vistas: model_probe, prompt_create/publish/rollback, safety_run_tests, benchmark_run, developer_mode_toggle, agent_draft_create

## 13. UX / Responsive

UI `/lottery/admin/ai` HTTP 200 post-bake; verificación visual browser autenticada pendiente (login interactivo). Modo desarrollador en layout.

## 14–21. Entrega operativa

| # | Ítem | Estado |
|---|------|--------|
| 17 | Backup | Sí — dump citado arriba |
| 18 | Commits | Pendiente en repo local (cambios UAT no necesariamente pusheados) |
| 19 | Imágenes | `jaios-app-backend:lottery-aiadmin-uat-p0-20260723b`, frontend `aiadmin-closeout-20260723` |
| 20 | Deploy | Sí — compose harden override |
| 21 | Riesgos | P0=6 en suite; tokens métrica=0; playground turn-3; Agente checklist incompleto; catálogo 7 loterías |

---

## Defectos encontrados → corregidos

1. Shadow route prompts registry → wrapper Admin Center DB  
2. Display prompt `vv2` → `v2`  
3. Suite 300 no sembrada si ya existía suite chica → ensure_seeded  
4. Pack titles humanos vía PACK_META  
5. Draft save 500 MissingGreenlet → refresh  
6. Publish sin benchmark / con P0 → gates  
7. Incidente draft activo → rollback v2  

## Riesgos pendientes (no cerrado)

- Instrumentar tokens/costo reales en métricas 7d  
- Propagar last_success del probe al dashboard  
- P0=6 suite / turn-3 playground memoria  
- Completar campos Agente checklist o documentar como clase C/D  
- Ampliar catálogo si hay más loterías en DB  
- Commit/push formal + evidencia screenshots UI autenticada
