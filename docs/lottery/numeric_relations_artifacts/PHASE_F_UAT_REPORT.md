# Fase F — UAT visual/funcional DEV (Motor Relaciones Numéricas)

**Fecha:** 2026-07-23 / 2026-07-24  
**Ambiente:** DEV únicamente (`jaios_lottery_dev` @ `127.0.0.1:5433`)  
**Producción:** no desplegado / no modificado  
**Sync:** no modificado  

## Veredicto

**GO CONDICIONADO**

Listo para Producción solo tras autorización expresa y después de cerrar los pendientes de chat multi-lotería / despliegue del stack completo (no el RC :3001 antiguo).

## 1. URLs / rutas validadas (DEV UAT local)

| Ruta | Notas |
|------|--------|
| `http://127.0.0.1:3011/login` | Login UI |
| `http://127.0.0.1:3011/lottery/admin/numeric-relations` | Panel admin (Fase C) |
| `http://127.0.0.1:8011/api/v1/health` | UAT API slim |
| `http://127.0.0.1:8011/api/v1/lottery/admin/numeric-relations/{tables,groups,lotteries,analyze}` | API admin |
| `http://127.0.0.1:8011/api/v1/lottery/chat/sessions` (+ messages) | Chat Lottery IA |

**Nota de despliegue:** el contenedor RC `jaios-lottery-web-rc` en `:3001` **no** contiene esta rama (404 en la ruta). El UAT se ejecutó contra frontend local Docker `:3011` + API UAT `:8011` sobre la misma DB DEV.

## 2. Usuarios / roles (sin contraseñas)

| Usuario | Rol / pertenencia | Uso |
|---------|-------------------|-----|
| `uat-nr-admin@example.com` | `owner` + `is_superadmin`, tenant `uat-numeric-relations` | Admin UI, API, chat |
| `uat-nr-client@example.com` | `lottery_client`, mismo tenant | Permisos negativos |

## 3. Rama / commits / rollback

- Rama: `feature/lottery-numeric-relations-motor`
- Commits base UAT: `459a799`, `3f4d134`, `cf4a732`
- Commit correcciones Fase F: `74b2fbf`
- Tag rollback vigente: `restore/lottery-pre-numeric-relations-motor-20260723` → `25ccd8aa…`  
  - **Hallazgo:** se esperaba `5136606`; el tag actual apunta a `25ccd8aa`. Ambos son anteriores al motor (`459a799`). Confirmar/re-etiquetar si se requiere exactamente `5136606`.
  - No se movió el tag durante Fase F.

## 4. Capturas obligatorias

Directorio: `docs/lottery/numeric_relations_artifacts/phase_f/screenshots/`

- Tabla 1 / Tabla 2: `A_tabla1.png`, `B_tabla2.png` (+ `01_`/`02_` browser)
- Agrupaciones / códigos 34 y 53: `C_groups_t1.png`, `C_code34_t1.png`, `C_groups_t2.png`, `C_code53_t2.png`
- Formulario: `D_form.png`, `D_selectors.png`, `D_validation.png`, `D_case1_ready.png`
- Casos: `E_case1*.png`, `E_case2*.png`, `E_case3.png`, `E_case4.png`, `E_case5*.png`
- Trazas / ranking: `F_case1_trace.png`, `E_case1_ranking.png`, `E_case2_ranking.png`
- Responsive: `G_tablet.png`
- Cliente denegado UI: `H_client_ui.png`

## 5. Casos UAT 1–5 (evidencia)

### Caso 1 — N=26 Leidsa últimas 10
- API + UI: compañeros **27, 38**; ranking ambos **score 0**; vecinos 68/76/92 **no** inventados como coincidencias.
- Draw `a1c9bcef-…` fecha `2026-06-23` números **29, 1, 26** (peers 29 y 01).
- Artefactos: `case1_26_leidsa_last10.json`, `E_case1*.png`.

### Caso 2 — N=34 todas
- Ranking motor/UI: **76→9**, **17→2**, compañeros 1/33/49 con **score 0** visibles.
- Artefactos: `case2_34_all.json`, `E_case2_ranking.png`.

### Caso 3 — varias loterías (45 Leidsa+Loteka últimas 20)
- Ambos nombres en ocurrencias; ranking consolidado; sin mezcla por fecha.
- Artefactos: `case3_45_multi.json`, `E_case3.png`.

### Caso 4 — sin resultados (100 en Anguila 08:00)
- `occurrences_found=0`, ranking `[]`, sin inventar.
- Artefacto: `case4_no_results.json`, `E_case4.png`.

### Caso 5 — posibles duplicados (58 Loteka todas)
- Metadata UI: `posibles duplicados por contenido (sync): true` y draw_ids separados.
- API: `possible_content_duplicate_draws_detected=true` con grupo `39cc602c…` / `ca93967b…`.
- Artefactos: `case5_58_loteka_dups.json`, `E_case5_metadata.png`.

## 6. Chat (5 consultas)

Artefactos JSON: `chat_q1.json` … `chat_q5.json`, más `chat_q3b.json` / `chat_q5b.json`.

| # | Prompt | Resultado UAT |
|---|--------|---------------|
| 1 | 26 últimas 10 Leidsa | OK — `structured_content.type=lottery_numeric_relations`, scores 0, disclaimer |
| 2 | 34 todas | OK — ranking 76/9 etc., disclaimer |
| 3 | 45 Leidsa y Loteka | **Fallo** — respuesta de aclaración de fecha (`lottery_error`), no ejecuta NR (también en sesión fresca) |
| 4 | compañeros del 18 | OK — pide K explícito 5/10/20/todas (sin default oculto) |
| 5 | Analiza el 26 | Sesión fresca: pide lotería (correcto). En sesión contaminada: mensaje de fecha erróneo |

## 7. Permisos

- Admin: 200 en `/tables`, `/analyze`, UI accesible.
- Cliente: **403** backend (`Permiso requerido: lottery_admin_ai o lottery.admin o lottery_admin_tools`). Evidencia: `client_tables_response.json`, `client_tables_browser.json`, `H_client_ui.png`.
- **Corregido en UAT:** se eliminó `lottery.statistics` de `_PERMS` del router admin (antes el cliente podía leer tablas/analizar).

## 8. Pruebas automatizadas

```
43 passed in 0.79s
```

Archivo: `docs/lottery/numeric_relations_artifacts/phase_f/PYTEST_NR.txt`  
Suite: `backend/tests/test_lottery_numeric_relations_*.py`

## 9. Fallos encontrados

1. RC `:3001` sin feature (404) — entorno no alineado con commits.
2. Schema DEV sin columnas Lottery 2.0/3.0 en `lottery_lotteries` → fallos ORM (mitigado en UAT con ALTER DEV + select de columnas mínimas).
3. Catálogo vacío en UI vía AI defaults (tabla prompts ausente) → endpoint `/lotteries` + fallback UI.
4. `_PERMS` incluía `lottery.statistics` → cliente no autorizado podía analizar (**NO-GO potencial**, corregido).
5. Chat multi-lotería “45 en Leidsa y Loteka” no enruta al tool NR.
6. Tag rollback no apunta a `5136606` sino a `25ccd8aa`.
7. Chat requería tabla `lottery_ai_usage` ausente en DEV (creada solo en DEV para UAT).

## 10. Fallos corregidos (código UAT)

1. `db_history.py`: select columnar (id/name/commercial_name/slug) ante drift de esquema.
2. `lottery_numeric_relations.py`: `_PERMS` sin `lottery.statistics`; endpoint `GET /lotteries`.
3. UI: carga catálogo desde `/lotteries`.
4. `scripts/uat_nr_dev_server.py`: monta `company_context` para login FE.

## 11. Pendientes

1. Desplegar frontend+API feature branch en el stack DEV “oficial” (reemplazar RC `:3001`) antes de Producción.
2. Corregir planner/understanding para “Analiza el 45 en Leidsa y Loteka.”
3. Confirmar punto de rollback tag → `5136606` si es requisito contractual.
4. Migraciones formales de columnas Lottery 2.0/3.0 / tablas AI en DEV (hoy ALTER ad-hoc solo DEV).
5. UAT chat UI visual en `/lottery/chat` (API chat sí validada; captura de UI conversacional pendiente de tiempo).

## 12. Confirmaciones

- **Sync no modificado:** sí.
- **Producción no modificada:** sí.
- **No fusión/limpieza de draws duplicados:** sí (metadata informa y mantiene separados).

## 13. Criterios NO-GO vs evidencia

| Criterio NO-GO | Estado |
|----------------|--------|
| Mezcla peers entre draw_id | No observado |
| Huawei inventa compañeros/scores | Casos 1–2 OK; chat 1–2 OK |
| Ranking UI ≠ motor | Alineado (76=9, 17=2, 27/38=0) |
| No autorizados acceden | Corregido → 403 |
| Tabla 1/2 mezcladas | Tabs separados OK |
| Ocultar score 0 | Visibles OK |
| Fusionar duplicados sync | No; metadata true + separated |
| Análisis inutilizable | Funciona en admin |

## 14. Parada

Fase F completada con **GO CONDICIONADO**.  
**No desplegar a Producción** hasta autorización expresa.
