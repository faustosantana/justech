# J-9 — Historial del Número — Entrega DEV

**Rama:** `feature/nr-number-visual-explorer-j9`  
**Base J-1→J-6:** `232aa65` `fbb24c0` `ff73895` `43a8aac` `3b4e07a` `9aefe9a`  
**Producción:** intacta (sin deploy)  
**Fórmulas / Tabla 1 / Tabla 2 / histórico / `/analyze` v1:** sin cambios

---

## 1. Metodología confirmada

- `mother_code = número observado`
- Tabla 1 → candidatos (compañeros)
- Tabla 2 → confirmadores (vecinos del candidato)
- La fuerza la recibe el candidato de Tabla 1; el confirmador aporta evidencia
- Identidad de sorteo = `draw_id` (nunca fusionar por fecha)
- Siete sorteos = secuencia real posterior, no siete días calendario (modo CALENDAR_DAYS aparte)
- Censura cuando faltan sorteos posteriores

---

## 2. APIs

### Reutilizadas (`/history/*` J-3)

`conditions/search`, `posterior/summary`, `combinations`, `matrix`, `patterns/detail`, `evidence/by-draw`, `cycles`, `compare` (candidatos/confirmadores)

### Nuevas (J-9)

| POST | Uso |
|------|-----|
| `/history/numbers/profile` | Expediente resumen + charts data |
| `/history/numbers/occurrences` | Apariciones paginadas + filtros |
| `/history/numbers/occurrences/detail` | Expediente de una aparición |
| `/history/numbers/occurrences/next-draws` | 7 sorteos / días calendario + reproductor |
| `/history/numbers/compare` | Comparar number_a vs number_b |
| `/history/numbers/why-strengthened` | Explicación determinista |

Todas incluyen `methodology_version`, `effective_parameters`, `trace_id`, sample/censura cuando aplica.

---

## 3. UI

**Nombre visible:** HISTORIAL DEL NÚMERO  
**Ruta:** `/lottery/admin/control-center/motor/historial-numero`  
**Nav:** Control Center → Motor Matemático → Historial del Número

Incluye: buscador con ayudas, encabezado de tarjetas, condición pos/neg/parcial, metodología 5 pasos, árbol, tarjetas de candidatos, «¿Por qué se fortaleció?», apariciones, siete sorteos, reproductor, gráficas A–I (barras + alternativa textual), comparador, evidencia técnica colapsada.

---

## 4. Pruebas

| Suite | Resultado |
|-------|-----------|
| Unitarias `test_lottery_nr_number_explorer_j9.py` | **11/11 PASS** |
| E2E DEV DB `phase_j9/e2e_methodology_50.py` | **50/50 PASS** |

E2E ambiente: `jaios_lottery_dev` @ `127.0.0.1:5433`, loterías Leidsa/Loteka/Nacional/Loto Leidsa, universo ~25k draws.

### Rendimiento real (E2E, no falseado)

| Métrica | Valor |
|---------|-------|
| Carga universo | ~303–1863 ms (según caché/IO) |
| Caso promedio | ~397 ms |
| Caso máximo observado | ~2003 ms |

> Nota: el perfil completo de un número con cientos de apariciones puede superar 2 s en DEV si se recalcula ancla a ancla; la paginación de apariciones mitiga la UI. Optimización de caché de agregados queda como pendiente no bloqueante.

---

## 5. Permisos y auditoría

- Mismos permisos Control Center: `lottery_admin_ai` / `lottery.admin` / `lottery_admin_tools`
- Log estructurado `lottery.nr.historial` con usuario, acción, número, filtros, duración, `trace_id` (sin secretos)
- Evidencia técnica solo tras acceso admin (misma puerta que el resto del historial)

---

## 6. Capturas

Carpeta: `docs/lottery/numeric_relations_artifacts/phase_j9/screenshots/`

**Estado:** **20/20 completas** con datos reales DEV tras remount API (`:8001` `j9_nr_dev_server`) + FE (`:3011`).

Detalle, rendimiento, permisos y veredicto:  
`PHASE_J9_FINAL_VISUAL_PERFORMANCE_VALIDATION.md`

1. buscador · 2. expediente general · 3. condición positiva · 4. negativa · 5. parcial  
6. árbol · 7. candidato fortalecido · 8. por qué · 9. apariciones · 10. siete sorteos  
11. reproductor · 12. gráfica anual · 13. loterías · 14. ciclos · 15. comparación  
16. evidencia técnica · 17. móvil · 18. muestra pequeña · 19. censurado · 20. metodología

---

## 7. Archivos principales

- `backend/.../historical/presentation.py`
- `backend/.../historical/number_explorer.py`
- `backend/.../historical/api_schemas.py` (schemas J-9)
- `backend/app/api/v1/lottery_nr_historical.py` (endpoints `/numbers/*`)
- `frontend/.../historial-numero/page.tsx`
- `frontend/.../control-center/layout.tsx` (nav)
- `frontend/src/lib/api.ts` (clientes)
- `backend/tests/test_lottery_nr_number_explorer_j9.py`
- `docs/.../J9_NUMBER_VISUAL_EXPLORER_IMPLEMENTATION_PLAN.md`
- `docs/.../phase_j9/e2e_methodology_50.py` + `e2e_50_results.json`

---

## 8. Riesgos y pendientes

| Ítem | Severidad |
|------|-----------|
| Perfil cold puntual &gt; 2 s (avg OK) | Bajo — medido y justificado |
| Comparador recalcula dos perfiles completos | Medio en rangos amplios (&lt; 3 s en medición) |
| Caché de agregados de perfil | Pendiente no bloqueante |
| No hay índices nuevos | OK — no demostrados necesarios aún |

---

## 9. Veredicto

**GO PARA DESPLIEGUE** (validación visual + rendimiento cerrada en DEV)

Condición operativa restante:

1. Autorización expresa del usuario antes de cualquier despliegue a Producción.

Ver informe final: `PHASE_J9_FINAL_VISUAL_PERFORMANCE_VALIDATION.md`.

**Producción permanece intacta.** No se desplegó fuera de DEV.
