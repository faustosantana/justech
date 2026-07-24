# Release Notes — Motor de Relaciones Numéricas (Release Candidate)

**Producto:** JAIOS / Resultados de Loterías — Lotería IA  
**Fase:** G — Release Candidate  
**Fecha:** 2026-07-24  
**Ambiente de este RC:** DEV oficial (`:3001` + API `:8001` → `jaios_lottery_dev`)  
**Producción:** no desplegado en este documento  

---

## Resumen funcional

Motor de Relaciones Numéricas sobre el universo fijo **1..100**:

- **Tabla 1 (madre):** `n ÷ 1220` → código por suma de dígitos → compañeros del mismo código.
- **Tabla 2 (confirmación):** `1220 ÷ n` → vecinos del código T2 (exclude self).
- **Análisis histórico:** ocurrencias reales donde `drawn_number = N`, agrupadas por **`draw_id`**, puntuación por coincidencia de vecinos, ranking completo incluyendo score 0.
- **Admin UI** de auditoría (tablas, grupos, análisis, trazas expandibles, metadata de dedupe).
- **API admin** + **tool pública** `lottery_analyze_numeric_relations`.
- **Chat Lottery IA:** Huawei interpreta intención y llama al motor; no calcula tablas/códigos/vecinos ni altera el ranking.

Aclaración obligatoria al usuario: señal histórica del método — **no es certeza ni garantía** ni recomendación de apuestas.

---

## Arquitectura

```
Usuario (UI admin / Chat)
        │
        ▼
API /lottery/admin/numeric-relations/*   ← permisos admin
Chat → planner → lottery_analyze_numeric_relations
        │
        ▼
analyze_from_db → analyze_observed_number   ← único motor
        │
        ▼
PostgreSQL DEV (lottery_draws / lottery_draw_numbers por draw_id)
```

- Identidad de sorteo = `lottery_draws.id` (`draw_id`).
- Peers vía FK `lottery_draw_numbers.draw_id`.
- Duplicados de contenido de sync: se informan en metadata y **permanecen separados**.

---

## Cambios realizados (alcance RC)

| Área | Cambio |
|------|--------|
| Motor | Tablas 1/2, scoring, historial por `draw_id`, metadata de dedupe |
| Admin UI | `/lottery/admin/numeric-relations` |
| API | tables, groups, lotteries, analyze |
| Tool/Chat | intent NR, planner un solo step, narrativa |
| Fase F UAT | permisos admin endurecidos; catálogo loterías; evidencia |
| Fase G | Enrutamiento multi-lotería (`Analiza el N en A y B`) |

**No incluidos:** cambios de sync, fusión de draws, cambios de fórmulas, predicciones.

---

## Commits incluidos

Ancestros requeridos + fix Fase G:

| Commit | Descripción |
|--------|-------------|
| `459a799` | Motor (tablas + análisis histórico) |
| `12e5542` | UI admin, API, tool/chat |
| `3f4d134` | Validación agrupación por `draw_id` |
| `cf4a732` | Fase E metadata / validación integral |
| `255cf9c` | Hardening UAT Fase F (permisos, schema adapter, evidencia) |
| `4c8e748` | Cierre referencias reporte Fase F |
| `8d1e1cd` | Fix multi-lotería intent/planner (Fase G) |

HEAD RC = tip de `feature/lottery-numeric-relations-motor` que contiene los anteriores.

---

## Riesgos conocidos

1. Schema DEV histórico incompleto vs modelo Lottery 2.0/3.0 (mitigado con selects columnares + ALTER DEV ad-hoc).
2. Stack RC usa superficie API slim (`scripts/rc_nr_dev_server.py`) porque `app.main` falla por módulo preexistente ausente (`integration_connector` schemas) — **ajeno al motor NR**.
3. Chat multi-lotería sin K explícito **aclara** 5/10/20/todas (política anti-default oculto); no inventa K.
4. Tag rollback `restore/lottery-pre-numeric-relations-motor-20260723` apunta a `25ccd8aa` (no `5136606`).

---

## Riesgos aceptados

1. Draws con mismo contenido y distinto `draw_id` se cuentan por separado (política sync no modificada).
2. Huawei puede pedir aclaración; no debe inventar lotería ni K.

---

## Rollback

- Tag: `restore/lottery-pre-numeric-relations-motor-20260723` → `25ccd8aa`
- Acción: redeploy código en ese commit; no revertir datos históricos de draws.
- Sync: no hay cambios de sync que revertir.

---

## Checklist de despliegue (alto nivel)

1. Confirmar GO / autorización expresa.
2. Backup BD + snapshot VPS.
3. Desplegar commits listados (sin sync write).
4. Migraciones formales si aplica (columnas Lottery 2.0/3.0 / tablas AI).
5. Restart API + frontend.
6. Smoke test (casos Fase G).
7. Verificar permisos 403.

Detalle: `PRODUCTION_DEPLOY_CHECKLIST.md`.

---

## Checklist post-deploy

1. Health API / UI login.
2. Admin NR: Tabla 1/2 visibles y separadas.
3. Análisis N=26 Leidsa y N=34 todas.
4. Chat multi-lotería con K explícito.
5. Usuario sin permiso → 403.
6. Logs sin errores de motor.
7. Confirmación: sync idle / no writes no autorizados.

---

## Tiempo estimado

| Actividad | Estimación |
|-----------|------------|
| Backup + snapshot | 15–30 min |
| Deploy + restart | 20–40 min |
| Smoke + validación | 30–45 min |
| **Total** | **~1.5–2 h** |

---

## Dependencias

- PostgreSQL con histórico lottery (`lottery_draws`, `lottery_draw_numbers`, `lottery_lotteries`).
- Redis (auth/sesiones según stack).
- Módulo `LOTTERY_MODULE_ENABLED=true`.
- Permisos admin para auditoría; tool chat con permisos de estadísticas/búsqueda según contrato.
- LLM/Huawei solo para interpretación (no para matemática).
