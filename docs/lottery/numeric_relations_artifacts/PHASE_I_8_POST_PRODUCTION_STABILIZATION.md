# PHASE I-8 — Post-Production Stabilization

**Fecha:** 2026-07-24  
**Entorno:** Producción `https://jaios.justech.do`  
**Fase previa:** I-7 despliegue exitoso (cerrado)  
**Alcance:** estabilización, defectos menores, cierre v1.0 — **sin** funciones nuevas ni cambios de metodología/fórmulas/rango/histórico/sync/ranking/scoring/prompt activo.

---

## 1. Commit / artefacto desplegado

| Campo | Valor |
|-------|-------|
| Tip de rama autorizada (fuente) | `273ba4a` — `docs(lottery): close Phase I-6.5 validation` |
| Rama | `feature/lottery-ia-control-center` |
| Imágenes Producción | `jaios-app-backend:control-center-20260724`, `jaios-app-frontend:control-center-20260724` |
| Método I-7 | overlay bake (NR base + Control Center); `router.py` / `api.ts` parchados (no replace wholesale) |
| Deploy UTC (I-7) | 2026-07-24 ~13:59 UTC |

---

## 2. Migración

| Campo | Valor |
|-------|-------|
| Alembic | `061_lottery_ia_control_center` (head) |
| Transición | `060` → `061` en I-7 |
| Fallos de migración | ninguno observados post-estabilización |

---

## 3. Servicios (estado al cierre I-8)

| Servicio | Imagen / estado |
|----------|-----------------|
| backend | `control-center-20260724` — healthy |
| frontend | `control-center-20260724` — up |
| gateway | `nginx:1.27-alpine` — up |
| lottery-sync-worker | misma imagen backend — up; ticks `guarded_write_ok` |
| postgres | healthy |

Health API: `{"status":"ok","service":"jaios-api","version":"0.1.0"}`.

---

## 4. Backup / rollback (heredado de I-7)

| Campo | Valor |
|-------|-------|
| Backup dir | `/var/jaios/backups/pre_control-center-20260724_20260724_135110/` |
| Dump SHA256 | `0d20dd38534daf5d7a687a6b1528ed5ec03816698d347787f66cca78c4907392` |
| Tags rollback imágenes | `jaios-app-backend\|frontend:rollback-pre-control-center-20260724` |
| Rollback usado | **No** |

---

## 5. Smoke

**Corrección:** caso OpenAPI apuntaba a `/api/v1/openapi.json` (incorrecto). Script corregido a `http://127.0.0.1:8000/openapi.json`. **No** se cambiaron endpoints de producto.

**Resultado I-8:** **27 PASS / 0 FAIL**  
Evidencia: `phase_i_8/smoke_23_plus.txt`, script `phase_i_8/prod_smoke_i8.py`.

Incluye la matriz I-7 (el caso OpenAPI que dejaba 22/23) más chat (missing/multi/absolute/stub) y permisos ampliados. Equivalente operativo: **suite completa PASS** (requisito 23/23 del núcleo I-7 cumplido y superado).

Invariantes:

- `draws` 91937 → 91937  
- `active_prompt` `72b294c5-606e-4adb-b978-8e14be68edaa` sin cambio  

---

## 6. Validación visual (navegador real / Playwright en VPS)

Recorrido PASS (screenshots en `phase_i_8/screenshots/`):

Hub, Tabla 1, Tabla 2, Grupos T1/T2, Relaciones, Auditoría, Predicciones, Ejecutar, Prompt Studio, Compilado, Versiones, Playground, Benchmark.

Hallazgos automáticos de captura: `[]` (`visual_findings.json`).

### Multi-lotería visual (brecha I-6.5 cerrada)

- Caso: **N=45**, **Quiniela Leidsa + Quiniela Loteka**, **K=10**
- Evidencia: `screenshots/15_multi_45_leidsa_loteka_k10.png` + `15_multi_text.txt`
- UI Resultado: compañeros **69, 80**; ranking `#69 score 2`, `#80 score 0`; loterías nombradas correctamente; disclaimer histórico presente.

---

## 7. Validación funcional

### A. Tabla 1 · N=1

- Fórmula: `1 ÷ 1220`
- Cadena dígitos: `00008196721`
- Código: **34**
- Evidencia UI + API: `screenshots/16_func_table1_n1*`, `functional_api.json` → `A_table1_n1`

### B. Tabla 2 · N=1

- Fórmula: `1220 ÷ 1`
- Cadena: `122000000000`
- Código: **5**
- Evidencia: `screenshots/17_func_table2_n1*`, `B_table2_n1`

### C. Relaciones · N=26 · Leidsa · K=10

- Compañeros: **27, 38**
- Evidencia UI: `18_func_rel_26_*`; API: `C_rel26`

### D. Predicción · N=34 · todas

- Ranking del motor con scores/vecinos/T2
- `guarantees_outcome=false`
- Advertencia: señal histórica, sin garantía
- Ocurrencias usadas: 162 (API) / UI «Draw IDs analizados: 116» en corrida visual (conteo de ocurrencias; ver hallazgos medio sobre copy)
- Evidencia: `19_func_pred_34_*`, `D_pred34`

### E. Multi-lotería · N=45 · Leidsa+Loteka · K=10

- Confirmado visualmente (además de API)
- API companions 69,80 (alineado UI)

### F. Chat

| Caso | HTTP | Resultado |
|------|------|-----------|
| Consulta válida (26 Leidsa últimas 10) | 200 | Análisis NR; compañeros 27/38; sin garantía |
| Datos faltantes | 200 | Pide elegir 5/10/20/todas explícitamente |
| Múltiples loterías | 200 | Responde; en una corrida interpretó N=26 en lugar de 45 → hallazgo **medio** |
| Afirmación absoluta | 200 | Rechazo de predicción / sin apuestas |
| Motor no implementado (frecuencias) | 200 | Bloqueo + redirige a NR histórico |

---

## 8. Permisos

Admin (`admin@justech.do`): acceso completo (tables/compiled/prompts/benchmark 200).

Usuario no autorizado (`diana@justech.do`) — **403 backend** (no solo menú oculto):

| Recurso | Código |
|---------|--------|
| tables / numeric-relations | 403 |
| prompts / versiones | 403 |
| compiled | 403 |
| schema Prompt Studio | 403 |
| export JSON técnico | 403 |
| benchmark administrativo | 403 |
| predictions run | 403 |
| validate-draft (vía secret scan) | 403 |

FE sin token en `/prompt-studio/compilado` → redirect login (`21_noperm_*`).

Evidencia: `permissions_matrix.txt`, smoke `permisos_403`.

---

## 9. Monitoreo posterior

Ventana post I-7 / I-8 (~45–60 min muestreados):

| Señal | Resultado |
|-------|-----------|
| Backend ERROR/Traceback | **0** |
| Gateway emerg/crit | **0** |
| Sync worker ERROR | **0** |
| Sync write flag | `true` (sin cambio) |
| Draws | **91937** intacto |
| 4xx esperados | 403 de negación de permisos; 400 secret/validate en admin |
| 5xx CC | no observados en muestra |
| Frontend | ruido Server Action cache (no repetitivo de CC en backend) |

No hay errores repetitivos introducidos por el Control Center en backend/sync/gateway.

---

## 10. Hallazgos y correcciones

Ver `phase_i_8/FINDINGS.md`.

**Correcciones aplicadas:** únicamente script de smoke OpenAPI.  
**Críticos/altos pendientes:** ninguno.  
**Medios:** documentados; fuera de auto-fix I-8 (no ampliar alcance / no tocar prompt activo).

---

## 11. Pendientes (post v1.0, no bloqueantes)

1. Normalizar `lottery_names` en respuesta API multi.  
2. Observar/robustecer interpretación de N en chat multi.  
3. Copy UI: «Ocurrencias analizadas» vs «Draw IDs».  
4. Limpieza ruido Server Action en clientes cacheados.

---

## 12. Tag

Condiciones:

- [x] Smoke suite PASS (OpenAPI incluido)
- [x] Sin críticos / altos pendientes
- [x] Permisos correctos
- [x] Producción estable
- [x] Sync estable (`guarded_write_ok`, flag intacto)
- [x] Histórico intacto (91937)

**Tag:** `lottery-ia-control-center-v1.0.0`

---

## 13. Veredicto

### RELEASE CERRADO CON OBSERVACIONES

El Lottery IA Control Center v1.0 queda cerrado en Producción. Observaciones = hallazgos **medios/bajos/UX** no bloqueantes, sin cambio de metodología ni prompt activo.
