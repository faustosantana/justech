# PHASE J-10F — Final Seven Lotteries Readiness

## Base

| Campo | Valor |
|-------|--------|
| Rama base | `feature/nr-j10-final-stabilization` @ `a510467` |
| Rama integración | `feature/nr-j10-final-seven-lotteries-integration` |
| Worktree | `/Users/faustosantana/Projects/justech-j10-final-scope` |
| Fuente J-10L | `feature/nr-j10-seven-lotteries-strict-scope` (base `3ccfff3`) |

## Cherry-picks J-10L

| SHA origen | Resultado |
|------------|-----------|
| `efafcb8` | OK → `dc5b08a` |
| `6e96db2` | OK → `35abba3` |
| `ef40467` | OK → `3923443` |
| `8b259d3` | OK → `e303863` |
| `ab22e29` | **conflicto** `motor-table.tsx` — resuelto fusionando: grilla sin columnas técnicas (J-10L) + CTA Analizar→expediente (J-10S) → `d97bf9c` |
| `ae2e1cc` | OK → `60568da` |
| `b03c1b3` | OK → `b8218f3` |
| `c62d088` | OK → `d9188bf` |

## Configuración DEV (is_featured)

Script: `scripts/j10f_set_final_featured_lotteries_dev.py`  
Evidencia: `phase_j10_final_scope/01_featured_audit_before.json`, `02_featured_after.json`

### Antes
Gana Mas, Loteria Nacional, **Loto Leidsa**, **Loto Real**, Quiniela Leidsa, Quiniela Loteka, Quiniela Real

### Después (exacto)

| Nombre DB | ID |
|-----------|-----|
| Loteria Nacional | `0118037f-8f8b-4a82-899c-42cd50b6e194` |
| Quiniela Leidsa | `523875dc-c7f4-4883-b0f6-b440397e3aeb` |
| Quiniela Loteka | `b9f2c5a2-bc3e-4382-9b6d-3cee16db00fd` |
| Gana Mas | `43250709-ee65-476f-91f6-cb8438f49d65` |
| Quiniela Real | `205c58d2-cfcf-44e6-894d-97358b3d540b` |
| New York 2:30 | `1c488641-adb6-4790-89e7-879d361da7cc` |
| New York 10:30 | `1624b6f2-88c6-42b5-a597-bf9c0f98a6b5` |

Desactivados (conservados): Loto Leidsa, Loto Real (+ resto archivado).  
**No se borraron** loterías ni sorteos.

## Validación API

Archivo: `phase_j10_final_scope/04_api_validation.json`  
Resultado: **ok=True** (33 checks PASS)

Incluye:
- catalog featured = 7 nombres exactos
- NR lotteries `scope=active` = 7; sin Anguila/Haití/Miami/Loto*
- archived contiene Loto Leidsa / Loto Real
- analyze con solo Loto Leidsa → rechazado
- profile 50/35/86 con `analysis_scope=FEATURED_SEVEN`, `active_lottery_count=7`
- charts sin Loto Leidsa
- permisos client 403/401, anon 401
- `production_forbidden=true`
- fórmulas internas intactas en `/tables`

## Caché / metadata

- `scope_set_hash` recalculado por conjunto activo
- Sin Redis NR previo; metadata adjunta en respuestas history/analyze
- Universo anterior (Loto*) no reutilizable vía featured flags

## Tabla 1 / 2

Vista principal: Número, Código, Compañeros/Confirmadores, Cantidad, Analizar.  
Cálculo técnico solo tras “Ver cálculo” (colapsado).

## Rendimiento (perfil ×3, ms)

Ver `04_api_validation.json` → `perf`.

## Capturas

`phase_j10_final_scope/screenshots/` (01–10)

## Producción

**Intacta.** Solo `jaios_lottery_dev`. Sin deploy.

## Veredicto

**GO PARA DESPLIEGUE** — condicionado a autorización expresa del usuario.

Criterios cumplidos:
- siete loterías exactas (NY 2:30 / 10:30, no Loto*)
- archivadas fuera de UI/cálculo activo
- históricos conservados
- T1/T2 simplificadas
- E2E API PASS
- permisos PASS
- production_forbidden
- DEV estable bajo rama de integración

No desplegado automáticamente.
