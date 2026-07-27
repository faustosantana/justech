# Informe de auditoría conversacional — Analista IA (LOTTERY)

**Fecha ejecución:** 2026-07-27T22:41Z → 22:50Z (UTC)  
**Modo:** SOLO AUDITORÍA — sin modificar código  
**Imagen prod:** `jaios-app-backend:lottery-ia-ux-v2.4.3`  
**Resultado global:** **BLOQUEADO**

---

## Entorno probado

- Producción `https://jaios.justech.do`
- Contenedor `jaios-app-backend-1` (healthy)
- Usuario API: `admin@justech.do` (JWT owner + tenant Justech Demo)
- Fuente de verdad: PostgreSQL `jaios` tablas `lottery_*`, contrastada de forma independiente
- Alcance “todas las loterías” del Analista = `DEFAULT_ALL_HISTORY_LOTTERIES` (Nacional / Nacional Día / Nacional Noche / Leidsa / Loteka / Real / Gana Más)

## Endpoint o flujo utilizado

1. `POST /api/v1/lottery/chat/sessions` — crear conversación  
2. `POST /api/v1/lottery/chat/sessions/{id}/messages` — mismo flujo que el frontend (`sendLotteryChatMessage`)  
Base interna: `http://127.0.0.1:8000/api/v1` (mismo servicio detrás de gateway)

## Conversation IDs

| Bloque | conversation_id |
|--------|-----------------|
| A | `5184ea9c-95f6-4aba-aefb-315ee9d3f0f4` |
| B | `83162ee9-170e-4e9e-86cd-73098c8f248e` |
| C | `e34d9629-4f28-413a-ad2b-7bb6d834ca9a` |
| D | `0b7e5de9-258a-4a5f-9487-0a8226dbd9be` |
| E | `d0492a55-2b78-4cfa-a34f-a643c9d278ce` |
| F | `920770ad-c2ea-4c83-99c0-f624d3da8a75` |
| G | `43ff24c2-62d6-4282-995d-153324b74a1a` |
| H | `bc6e77db-707e-418e-9db2-cb3367cad723` |

Raw JSON: `evidence/lottery-analyst-conversation-audit-20260727/raw_results.json`

---

## Cantidades

| Métrica | Valor |
|---------|-------|
| Turnos totales | 44 |
| PASS | 12 |
| FAIL | 32 |
| Puntuación global (media de 12 criterios × 44 turnos) | **41.3%** |
| Exactitud factual (turnos con dato histórico) | **38%** (fallos críticos con dato inventado/equivocado) |
| Continuidad | **34%** |
| Naturalidad media | **3.4 / 5** |
| Interpretación media | **2.8 / 5** |
| Contradicciones internas | **≥ 6** |
| Jerga interna detectada | **sí** (`last_n_occurrences`, `compare_a_lotteries`) |
| Fallos críticos (bloquean) | **≥ 6** |

---

## Fallos críticos (auto-BLOQUEADO)

1. **Sujeto equivocado A.7:** «últimas 4 del 35» → tool/contexto usaron **04**; structured_content lista apariciones del 04.  
2. **Sujeto equivocado E.1:** «últimas 5 del 54» → usaron **05**.  
3. **Cero inventado C.1:** «55 y 24 el mismo día» → «no encontré coincidencias»; repo core tiene múltiples fechas (p.ej. 2026-07-19). Tool erróneo: `complete_analysis` en vez de same_day.  
4. **Dato inventado D.1:** afirma 94 con **4** apariciones; repo core ≈ **599**.  
5. **Fecha inventada F.2:** 44 → «10 de mayo de 2025 / La Primera Tarde»; repo core última ≈ **2026-07-20 Quiniela Leidsa**.  
6. **Contradicción G.2:** texto Loteka 10-jul pos1 vs «Lotería: Nacional Noche» y evidence last 17-jul pos2; filtro primera posición no aplicado correctamente.

Otros bloqueadores de umbral: continuidad rota (A.6, B, D, E, F.3, H.4+), HTTP 500 (B.4, E.2), jerga interna visible, consultas sin completar.

---

## Causas raíz agrupadas

| Capa | Fallos |
|------|--------|
| **Clasificación / extracción de número** | Límite `N` se interpreta como sujeto `0N` (A.7, E.1); «las otras tres» → posiciones (F.3) |
| **Planner / selección de herramienta** | Pareja same_day → `complete_analysis` (C); comparación 54/94 incompleta/sesgada (D); after-window 500 (E.2) |
| **Herencia de contexto** | No hereda Nacional en B; pierde pareja/números en D; H no reutiliza última aparición al corregir a 97 |
| **Formatter / evidence** | Narrativa dice 35 pero facts=04; jerga `last_n_occurrences`; contradicción Loteka vs Nacional |
| **Runtime / estabilidad** | «No pude completar…» (B.1, G.3, H.10); HTTP 500 (B.4, E.2) |
| **Modelo (síntesis)** | Inventa conteos (D.1 94=4); «ayer» relativo dudoso; no lista las 3/4/5 fechas en prosa pese a tener items |

---

## Resultados reales contrastados (muestra)

| Caso | Repositorio (alcance default RD) | Analista |
|------|----------------------------------|----------|
| Último 22 | 2026-07-20 Gana Más pos 2 | OK |
| Último 35 | 2026-07-21 Quiniela Real pos 1 | OK (como «Real») |
| Último 97 | 2026-07-18 Lotería Nacional pos 2 | OK (Nacional Noche) |
| Últimas 3 del 97 | 18 Nacional, 15 Real, 11 Nacional | Structured OK; prosa incompleta + jerga |
| Últimas 4 del 35 | 21 Anguila/Real/Gana… (según filtro) | **FAIL → consultó 04** |
| 35 Nacional pos1 | 2026-07-20 Nacional | B.1 no completó |
| 55+24 same day | ≥10 fechas en core | **FAIL → cero** |
| 54 vs 94 totales core | ~573 / ~599 | **FAIL → 223 / 4** |
| Último 44 core | 2026-07-20 Leidsa | **FAIL → 2025-05-10** |

---

## Matriz de evaluación por turno

Escala 0–5 por criterio: C1 comprensión, C2 factual, C3 continuidad, C4 alcance, C5 tools, C6 coherencia, C7 naturalidad, C8 claridad, C9 interpretación, C10 sin jerga, C11 sin herencia mala, C12 reconoce falta evidencia.

| Turno | PASS/FAIL | Media | Causa corta |
|-------|-----------|-------|-------------|
| A.1 Hola | PASS | 4.8 | Natural, sin investigación |
| A.2 último 22 | PASS | 4.6 | Fecha/lotería/posición OK |
| A.3 último 35 | PASS | 4.4 | OK; «ayer» menor |
| A.4 último 97 | PASS | 4.6 | OK vs core |
| A.5 últimas 3 del 97 | FAIL | 2.9 | Intent OK + items OK; prosa no lista fechas; jerga `last_n_occurrences` |
| A.6 dos anteriores | FAIL | 1.5 | Pierde continuidad; pide número con 97 activo |
| A.7 últimas 4 del 35 | FAIL | 0.8 | **Sujeto 04**; contradicción texto/facts |
| B.1 35 Nacional 1ª | FAIL | 0.5 | No completa; no aplica Nacional |
| B.2 últimas 3 | FAIL | 1.8 | No hereda Nacional; all-lotteries pos1 |
| B.3 todas posiciones | FAIL | 2.0 | Pide aclaración innecesaria |
| B.4 todas loterías | FAIL | 0.0 | HTTP 500 |
| B.5 más reciente | FAIL | 1.5 | Pide lotería; no responde |
| C.1 55+24 same day | FAIL | 0.7 | **Cero falso**; tool wrong |
| C.2 en Nacional | FAIL | 1.0 | Parte de cero falso |
| C.3 primera pos | FAIL | 1.0 | Idem |
| C.4 todas pos | FAIL | 1.0 | Idem |
| C.5 último 97 | PASS | 4.5 | Cambia foco OK |
| C.6 últimas 3 | FAIL | 3.0 | Datos OK; jerga; prosa pobre |
| D.1 compara 54/94 | FAIL | 1.2 | **Conteos inventados**; no compara ambos bien |
| D.2 solo 2026 | FAIL | 1.5 | No ejecuta; pregunta de más |
| D.3 primera pos | FAIL | 1.5 | Pierde continuidad de comparación |
| D.4 más reciente | FAIL | 1.0 | Olvida 54 y 94 |
| E.1 últimas 5 del 54 | FAIL | 0.7 | **Sujeto 05** |
| E.2 D+1..D+3 | FAIL | 0.0 | HTTP 500 |
| E.3 misma lotería | FAIL | 1.0 | Hereda 05 |
| E.4 cualquier lotería | FAIL | 1.2 | Sin foco |
| F.1 ¿Cuándo salió? | PASS | 4.7 | Pide solo número |
| F.2 El 44 | FAIL | 1.0 | **Fecha inventada** + alias ambiguo |
| F.3 otras tres | FAIL | 1.3 | Confunde con posiciones |
| G.1 01+99 cero | PASS | 4.5 | Cero real OK |
| G.2 88 primera | FAIL | 1.5 | Contradicción / filtro pos |
| G.3 conteo 1 Nacional 2026 | FAIL | 0.5 | No completa (y sujeto «1» frágil) |
| G.4 último 35 | PASS | 4.3 | OK factual |
| H.1 último 22 | PASS | 4.6 | OK |
| H.2 Gracias | PASS | 4.2 | Natural |
| H.3 Perfecto | PASS | 4.0 | Natural (genérico) |
| H.4 me refiero al 97 | FAIL | 2.0 | No corrige a última aparición; menú |
| H.5 no fue lo que pregunté | FAIL | 2.2 | No relee intención previa |
| H.6 Revísalo | FAIL | 2.0 | No re-consulta 97 |
| H.7 ¿Seguro? | FAIL | 2.0 | No verifica dato |
| H.8 más simple | FAIL | 2.5 | No aporta contenido |
| H.9 solo respuesta | FAIL | 2.0 | Sigue sin dato |
| H.10 análisis profundo | FAIL | 0.5 | No completa |
| H.11 qué llama atención | FAIL | 2.0 | Sin evidencia |

**PASS=12 / FAIL=32**

---

## Transcripción completa (resumen por bloque)

### Bloque A — `5184ea9c-…`
1. **Hola, ¿cómo estás?** → «Hola, estoy muy bien. ¿Qué te gustaría investigar hoy?»  
2. **¿Cuándo fue la última vez que salió el 22?** → 20-jul-2026 Gana Más 2ª (OK)  
3. **… el 35?** → 21-jul-2026 Real 1ª (OK)  
4. **¿Y el 97…?** → 18-jul-2026 Nacional Noche 2ª (OK)  
5. **¿Y las últimas 3 veces?** → intent last_n; items 18/15/11; prosa + jerga  
6. **Dame las dos anteriores a esas.** → «¿A qué número te refieres?» (FAIL)  
7. **Ahora las últimas 4 del 35.** → texto habla de 35; facts/contexto **04** (FAIL crítico)

### Bloque B — `83162ee9-…`
1. 35 Nacional 1ª → «No pude completar…»  
2. ¿Y las últimas 3? → 35 pos1 en Real/Nacional/Real (sin filtro Nacional)  
3. Todas posiciones → pide lotería  
4. Todas loterías → HTTP 500  
5. ¿Cuál fue la más reciente? → pide lotería

### Bloque C — `e34d9629-…`
1–4. 55+24 same day (y filtros) → afirma cero (FAIL vs repo)  
5–6. Cambio a 97 → última OK; last 3 con jerga

### Bloque D — `0b7e5de9-…`
1. Compara 54/94 → 223 vs 4 (falso)  
2–4. 2026 / primera / más reciente → no mantiene comparación

### Bloque E — `d0492a55-…`
1. Últimas 5 del 54 → consulta **05**  
2. Tres días siguientes → 500  
3–4. Misma/cualquier lotería → contexto corrupto (05)

### Bloque F — `920770ad-…`
1. ¿Cuándo salió? → pide solo número (OK)  
2. El 44. → fecha 2025-05-10 (FAIL)  
3. ¿Y las otras tres? → interpreta posiciones

### Bloque G — `43ff24c2-…`
1. 01+99 Nacional 1ª → cero OK  
2. 88 primera → contradicción Loteka/Nacional  
3. conteo «1» Nacional 2026 → no completa  
4. último 35 → OK

### Bloque H — `bc6e77db-…`
1. último 22 OK  
2–3. Gracias / Perfecto OK genérico  
4–11. Corrección a 97 y pedidos de verificación/análisis → no re-ejecuta consulta factual; H.10 falla

---

## Recomendación final

**Resultado: BLOQUEADO**

No desplegar ni dar por funcional el Analista conversacional hasta corregir, en origen (sin hardcodes de prueba):

1. Extracción de sujeto vs límite (`últimas N del X` / `últimas N` heredando X) — regresión A.7/E.1.  
2. Planner same_day para parejas — no `complete_analysis`.  
3. Comparación bilateral con frecuencias del repositorio (no síntesis inventada).  
4. Herencia selectiva de lotería/posición (Bloque B/D).  
5. Scrub de jerga (`last_n_occurrences`, `compare_a_lotteries`).  
6. Estabilidad: eliminar 500 / «No pude completar» en turnos estándar.  
7. Continuación «anteriores a esas» y corrección «me refiero al 97» deben reconsultar sin menú vacío.

**Esperar autorización explícita antes de cualquier corrección de código.**
