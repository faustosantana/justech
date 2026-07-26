# 31 — Seguimiento Q1–Q10 (tasas, posiciones, perfiles)

Fuente: activaciones únicas `(fecha, fuerte)` = **2222** · misses exactos = **552**  
Artefactos: `artifacts/deep_mathematical_audit/followup_q1_q10/`

Definición de oportunidad T1: en cada activación, si el grupo T1 del fuerte tiene un número en la distancia `d = pos(result) − pos(fuerte)`, cuenta 1 oportunidad. Un “hit” es que ese número exacto aparezca en D+1…D+7.

---

## 1. Distancia T1 — oportunidades y tasa

| Dist | Oportunidades | Apareció en ventana | Tasa |
|-----:|--------------:|--------------------:|-----:|
| −1 | 1545 | 1198 | **77.54%** |
| 0 (fuerte) | 2222 | 1670 | **75.16%** |
| +1 | 1506 | 1104 | **73.31%** |
| −2 | 1150 | 872 | **75.83%** |
| +2 | 1011 | 777 | **76.85%** |
| −3 | 648 | 483 | 74.54% |
| +3 | 701 | 539 | 76.89% |

CSV completo: `followup_q1_q10/q1_t1_distance_rates.csv`

**Hecho observado:** con oportunidad comparable, **−1 (77.54%) supera a +1 (73.31%)** y también a 0 (75.16%).

---

## 2. −1, +1, −2, +2 por D+1 / D+2 / D+3

(Primera aparición del número que ocupa esa distancia.)

| Dist | Opp | Hit ≤7d | 1ª en D+1 | 1ª en D+2 | 1ª en D+3 | 1ª en D+1…D+3 (% opp) |
|-----:|----:|--------:|----------:|----------:|----------:|----------------------:|
| −1 | 1545 | 1198 | 291 | 229 | 206 | **46.99%** |
| +1 | 1506 | 1104 | 271 | 221 | 203 | 46.15% |
| −2 | 1150 | 872 | 222 | 175 | 141 | 46.78% |
| +2 | 1011 | 777 | 190 | 147 | 133 | 46.49% |

CSV: `q2_adjacent_by_day.csv`

---

## 3. Número exacto en cada posición (ejemplos + catálogo)

Orden canónico = sorted(grupo T1). Catálogo 1–100: `q3_numbers_at_t1_positions.csv`

| Fuerte | Grupo T1 | Pos F | −2 | −1 | 0 | +1 | +2 |
|-------:|----------|------:|---:|---:|--:|---:|---:|
| 42 | 5 10 42 | 3 | 5 | 10 | 42 | — | — |
| 94 | 9 14 30 41 46 62 78 94 | 8 | 62 | 78 | 94 | — | — |
| 70 | 22 59 70 75 91 | 3 | 22 | 59 | 70 | 75 | 91 |
| 54 | 6 11 43 54 86 | 4 | 11 | 43 | 54 | 86 | — |
| 69 | 69 80 | 1 | — | — | 69 | 80 | — |

---

## 4. Los 552 misses — primer relacionado

CSV: `q4_misses_first_related.csv` (552 filas).

### A) Primer número con cualquier relación (cronológico)

| Primary del 1er relacionado | n |
|-----------------------------|--:|
| RELACION_DE_TERCER_NIVEL | 241 |
| RELACION_DE_SEGUNDO_NIVEL | 162 |
| MISMO_GRUPO_T2 | 53 |
| CANDIDATO_ORIGINAL_ALTERNATIVO | 34 |
| COMPANERO_DEL_CONFIRMADOR | 33 |
| MISMO_GRUPO_T1 | 29 |

Casi siempre en **D+1** (550/552). Lotería dominante del primer hit: **Gana Más** (497).

### B) Primer compañero T1 (familia del fuerte)

| Métrica | Valor |
|---------|------:|
| Misses con al menos un compañero T1 en ≤7d | **507 / 552** |
| Sin compañero T1 en ventana | 45 |

Distancia T1 del primer compañero (entre los 507):

| Dist T1 | n |
|--------:|--:|
| +1 | 120 |
| −1 | 101 |
| −2 | 72 |
| +2 | 64 |
| otras | 150 |

Día del primer compañero T1: D+1=284 · D+2=97 · D+3=65 · D+4…D+7=61

Cada fila del CSV trae: fuerte, primer relacionado, labels, `t1_pos`, día, lotería, posición de sorteo, y columnas `first_t1_*`.

---

## 5. Veinte cadenas más repetidas (O→F←C→R)

Detalle JSON: `q5_top20_chains.json`

| Cadena | Activaciones | Apariciones R | Años | Excepciones (R no salió) |
|--------|-------------:|--------------:|------|-------------------------:|
| 45→69←57→49 | 16 | 39 | 2019–2026 | 1 |
| 40→72←26→6 | 14 | 39 | 2019–26 (sin 2022) | 0 |
| 37→42←44→2 | 17 | 39 | 2020–2025 | 2 |
| 44→70←22→61 | 19 | 39 | 2020–2026 | 3 |
| 44→70←22→22 | 19 | 39 | 2020–2026 | 2 |
| 44→70←22→32 | 19 | 39 | 2020–2026 | 1 |
| 44→70←22→34 | 19 | 39 | 2020–2026 | 2 |
| 52→65←37→49 | 14 | 38 | 2019–26 (sin 2024) | 0 |
| 39→94←84→57 | 20 | 38 | 2019–26 (sin 2025) | 2 |
| 48→73←23→51 | 14 | 38 | 2020–22,25–26 | 3 |
| 44→70←22→86 | 19 | 38 | 2020–2026 | 2 |
| 49→35←44→16 | 13 | 38 | varios | 2 |
| 42→7←29→25 | 16 | 37 | 2019–2024 | 2 |
| 38→20←2→61 | 16 | 37 | 2019–2026 | 3 |
| 39→94←84→5 | 20 | 37 | 2019–26 (sin 2025) | 3 |
| 39→94←84→82 | 20 | 37 | 2019–26 (sin 2025) | 1 |
| 40→19←86→78 | 16 | 37 | 2020,23–26 | 3 |
| 37→42←44→1 | 17 | 37 | 2020–2025 | 3 |
| 44→70←22→47 | 19 | 37 | 2020–2026 | 5 |
| 44→70←22→93 | 19 | 37 | 2020–2026 | 2 |

Días y posiciones por cadena: ver JSON (`days`, `draw_positions`, `lotteries`, `exception_dates_no_result`).

---

## 6. Perfil completo del 42

JSON: `q6_profile_42.json`

| Campo | Valor |
|-------|--------|
| Código T1 | 37 |
| Grupo T1 ordenado | **5, 10, 42** |
| Posición del 42 | **3** |
| −2 / −1 / 0 | **5 / 10 / 42** (sin +1/+2) |
| Código T2 | (ver JSON) |
| Veces fuerte (únicas/día) | **85** |
| Exacto en ≤7d | **69 / 85 (81.18%)** |
| Años como fuerte | 2019–2026 |
| Origen dominante | **37** (109 cadenas) |
| Confirmadores top | 44, 9, 22, 90, 53 |
| Como origen / confirmador | ver JSON |

---

## 7. Perfil completo 39 → 94 ← 84

JSON: `q7_profile_39_94_84.json`

| Campo | Valor |
|-------|--------|
| Activaciones | **20** |
| Años | 2019,2020,2021,2022,2023,2024,2026 (sin 2025) |
| Exacto del 94 | **85.0%** de esas activaciones |
| Grupo T1 del 94 | 9 14 30 41 46 62 78 **94** (pos 8) |
| −1 / −2 | **78 / 62** |
| Resultados posteriores top | 57(38), 5(37), 82(37), 20(36), 61(36)… |

---

## 8. Transición Gana Más → Nacional → Real

JSON: `q8_lottery_transition.json`

| Campo | Valor |
|-------|------:|
| Filas aparición con esa tripleta | **1492** |
| Activaciones con origen Gana Más + confirmador Nacional | **72** |

Qué significa: en 72 cadenas el origen vino de **Gana Más** y el confirmador de **Lotería Nacional**; de esas cadenas, 1492 apariciones posteriores cayeron en **Quiniela Real**.

Primarios más frecuentes en esas filas: 3er nivel (440), sin relación (385), 2º nivel (331), mismo grupo T2 (111)…

No implica causalidad entre loterías; describe la co-ocurrencia observada origen→confirmador→resultado.

---

## 9. ¿La dirección negativa T1 (−1) es universal?

JSON: `q9_negative_direction_scope.json`

| Pregunta | Respuesta observada |
|----------|---------------------|
| ¿En todos los años? | **Sí** — hit en 2019…2026 (tasas 70–82%) |
| ¿En todos los grupos T1 con oportunidad? | **Sí** entre códigos que tienen posición −1 |
| ¿En todos los fuertes con oportunidad? | **Sí — 56/56** fuertes con opp −1 tuvieron ≥1 hit |
| ¿Solo en algunos números? | No: todos los fuertes con −1 disponible registraron hits; las tasas varían por número |

Tasa global −1: **77.54%** (1198/1545).

---

## 10. ¿Existe la secuencia fuerte → pos −1 → pos −2?

JSON: `q10_sequence_minus1_minus2.json`

Definición: primera aparición con `día(F) < día(n@−1) < día(n@−2)` dentro de D+1…D+7.

| Métrica | Valor |
|---------|------:|
| Activaciones con −1 y −2 existentes en el grupo | 1150 |
| Secuencia completa observada | **55** |
| Tasa | **4.78%** |
| Solo F luego −1 | (ver JSON) |
| Solo −1 luego −2 (sin exigir F) | (ver JSON) |

**Sí existe**, pero es **infrecuente** (~1 de cada 21 oportunidades con ambas posiciones).

Ejemplo: 2019-08-27 · fuerte 44 → 28 (−1) → 12 (−2) en días 4 < 5 < 6.

---

## Archivos

```
artifacts/deep_mathematical_audit/followup_q1_q10/
  q1_t1_distance_rates.csv
  q2_adjacent_by_day.csv
  q3_numbers_at_t1_positions.csv
  q4_misses_first_related.csv
  q5_top20_chains.json
  q6_profile_42.json
  q7_profile_39_94_84.json
  q8_lottery_transition.json
  q9_negative_direction_scope.json
  q10_sequence_minus1_minus2.json
  summary.json
```
