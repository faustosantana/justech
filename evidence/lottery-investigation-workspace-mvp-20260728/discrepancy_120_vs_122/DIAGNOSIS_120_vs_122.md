# Discrepancia 120 (PROD) vs 122 (DEV) — 35+14 same-day

**Fecha del diagnóstico:** 2026-07-29T01:31Z  
**Clasificación:** **D** — causa demostrada: divergencia asimétrica de sync entre ambientes.  
Las 2 coincidencias extra en DEV son **datos legítimos** (aparecen 35 y 14 el mismo día calendario en el alcance oficial), no duplicados, no fuera de alcance, no diferencia de consulta.

No se ajustó el número. No se cambió SQL ni código.

---

## Clasificación (checklist)

| Opción | ¿Aplica? | Motivo |
|--------|----------|--------|
| A. DEV más reciente y 122 correcto | Parcial | DEV sí tiene NY/Gana Más/Real más recientes (hasta 2026-07-23) que crean +2; pero PROD está **más adelante** en Nacional/Leidsa/Loteka (hasta 2026-07-27). |
| B. PROD correcto; DEV inválido/duplicado | **No** | Las +2 no son duplicados (`DUP_DN=0`). Son fechas con 35+14 reales en DEV. |
| C. Consultas no equivalentes | **No** | Misma SQL / mismos `lottery_id` / intersección exacta 120. |
| **D. Otra causa demostrada** | **Sí** | Sync asimétrico: DEV tiene draws NY (y Gana Más/Real) del 22–23/jul que PROD no tiene; PROD tiene draws posteriores de Nacional/Leidsa/Loteka que no añaden coincidencias 35+14. |

**Veredicto operativo para Workspace MVP en DEV:** **122 es el total correcto del dataset DEV actual.** Documentar cambio de baseline respecto a Beta 2.1 (120).

---

## 1. Fecha/hora máxima de datos

| Métrica | DEV (`jaios_lottery_dev@5433`) | PROD (`jaios` / `jaios-app-postgres-1`) |
|---------|--------------------------------|----------------------------------------|
| `max(draw_date)` oficial 7 | **2026-07-23** | **2026-07-27** |
| `max(created_at)` oficial 7 | 2026-07-26 03:40:41.644205+00 | 2026-07-28 01:04:47.056531+00 |
| `max(updated_at)` oficial 7 | 2026-07-26 03:40:41.644205+00 | 2026-07-28 01:04:47.056531+00 |
| `max(draw_date)` global | 2026-07-23 | 2026-07-27 |
| TZ sesión DB | UTC | UTC |
| `now()` al medir | 2026-07-29 01:31:04+00 | 2026-07-29 01:31:38+00 |

---

## 2. Cantidad de sorteos/registros (7 oficiales)

| Ambiente | draws oficiales | draw_numbers oficiales | draws all | draw_numbers all | lotteries |
|----------|-----------------|------------------------|-----------|------------------|-----------|
| DEV | 27 230 | 81 690 | 91 941 | 388 818 | 50 |
| PROD | 27 238 | 81 714 | 91 949 | 388 842 | 50 |

### Por lotería

| Lotería | lottery_id (igual en ambos) | source_id | DEV draws / max date | PROD draws / max date | Δ draws |
|---------|-----------------------------|---------|----------------------|-----------------------|---------|
| Gana Mas | `43250709-…` | 12 | 3859 / 2026-07-23 | 3857 / 2026-07-21 | +2 DEV |
| Loteria Nacional | `0118037f-…` | 4 | 3980 / 2026-07-23 | 3985 / 2026-07-27 | −5 DEV |
| New York 10:30 | `1624b6f2-…` | 17 | 3561 / 2026-07-23 | 3560 / 2026-07-21 | +1 DEV |
| New York 2:30 | `1c488641-…` | 16 | 3575 / 2026-07-23 | 3573 / 2026-07-21 | +2 DEV |
| Quiniela Leidsa | `523875dc-…` | 5 | 4052 / 2026-07-23 | 4057 / 2026-07-27 | −5 DEV |
| Quiniela Loteka | `b9f2c5a2-…` | 6 | 4083 / 2026-07-23 | 4088 / 2026-07-27 | −5 DEV |
| Quiniela Real | `205c58d2-…` | 13 | 4120 / 2026-07-23 | 4118 / 2026-07-21 | +2 DEV |

`lottery_id` / `source_id` **idénticos**. Aliases oficiales: **21 = 21**, set equal.

---

## 3. Consulta SQL exacta (ambos ambientes)

Equivalente a `LotteryRepository.same_day_number_coincidences` + filtro de las 7 oficiales:

```sql
SELECT lottery_draws.draw_date AS dd,
       count(distinct(lottery_draw_numbers.number_value)) AS nuniq
FROM lottery_draws
JOIN lottery_draw_numbers ON lottery_draw_numbers.draw_id = lottery_draws.id
WHERE lottery_draw_numbers.number_value IN ('35', '14')
  AND lottery_draws.lottery_id IN (
    '43250709-ee65-476f-91f6-cb8438f49d65',  -- Gana Mas
    '0118037f-8f8b-4a82-899c-42cd50b6e194',  -- Loteria Nacional
    '1624b6f2-88c6-42b5-a597-bf9c0f98a6b5',  -- New York 10:30
    '1c488641-adb6-4790-89e7-879d361da7cc',  -- New York 2:30
    '523875dc-c7f4-4883-b0f6-b440397e3aeb',  -- Quiniela Leidsa
    'b9f2c5a2-bc3e-4382-9b6d-3cee16db00fd',  -- Quiniela Loteka
    '205c58d2-cfcf-44e6-894d-97358b3d540b'   -- Quiniela Real
  )
GROUP BY lottery_draws.draw_date
HAVING count(distinct(lottery_draw_numbers.number_value)) >= 2
ORDER BY lottery_draws.draw_date DESC
LIMIT 500;
```

Resultado de esa query:

- DEV: **122**
- PROD: **120**

Agrupación: `lottery_draws.draw_date` (tipo `date`, calendario). Ambas sesiones en **UTC**. No hay conversión TZ en el GROUP BY.

---

## 4. Filas en DEV y no en PROD (coincidencias)

Intersección: **120**. Solo PROD: **∅**. Solo DEV: **2 fechas**.

### 2026-07-23 (DEV only)

| number | lottery | position | draw_id | draw_number_id |
|--------|---------|----------|---------|----------------|
| 14 | Quiniela Leidsa | 2 | `507c1ca9-47c6-45ba-8140-5dc84225d13c` | `909e8213-dea4-445c-8069-4eb0cb4a27d4` |
| 35 | New York 10:30 | 1 | `b80fabf2-85de-4366-8ade-f8c6de401dd1` | `1c7a166d-a7f7-4d38-affe-d75ace31e3d9` |

### 2026-07-22 (DEV only)

| number | lottery | position | draw_id | draw_number_id |
|--------|---------|----------|---------|----------------|
| 14 | Loteria Nacional | 1 | `3aa518e2-a381-45b7-8c5e-7e19825dc8d5` | `adfc905b-7a4c-411b-a213-8bb9c6f236c4` |
| 14 | Quiniela Leidsa | 2 | `6fff8fd6-35ba-4ad2-9a52-ef8c4b1d976c` | `a7a1ed13-c8cc-4937-8ec5-2ef3625ba1e2` |
| 35 | New York 2:30 | 1 | `69f3cf8d-490a-4be2-ac7e-67ec4dc148c5` | `ae765922-4259-47b5-bd30-fc11a50aad17` |

En PROD esas fechas **sí** tienen Nacional/Leidsa/Loteka (con **14**), pero **no** tienen draws de New York / Gana Más / Real → falta el **35** → no cuentan como coincidencia.

---

## 5. Filas en PROD y no en DEV

**Ninguna** fecha de coincidencia 35+14.

(PROD sí tiene draws posteriores 2026-07-24…27 en Nacional/Leidsa/Loteka; no generan par 35+14 adicional.)

---

## 6. Duplicados potenciales

| Check | DEV | PROD |
|-------|-----|------|
| `DUP_DN` (mismo date+lottery+number+position >1) | **0** | **0** |
| `DUP_DRAW` (mismo date+lottery >1 draw) | 2 pares | mismos 2 pares (IDs idénticos) |

Pares `DUP_DRAW` (no explican +2 coincidencias; existen en ambos y el dedupe del query service ignora keys repetidas):

- 2026-01-25 Quiniela Loteka ×2 draws
- 2026-01-20 New York 2:30 ×2 draws

---

## 7. Aliases / lottery_id

- 7 oficiales: mismos UUID y `source_id` en DEV y PROD.
- 21 aliases oficiales: sets iguales.
- No hay diferencia de resolución de alias que explique 120 vs 122.

---

## 8. Zona horaria / agrupación por fecha

- Ambas DB: `TIMEZONE=UTC`.
- Coincidencia definida por `draw_date` (date), no por timestamp local.
- Sin evidencia de shift TZ que cree/elimine días.

---

## 9. Las 2 coincidencias adicionales son…

| Hipótesis | Evidencia |
|-----------|-----------|
| Datos nuevos legítimos | **Sí (en DEV):** 35 (NY) + 14 (Leidsa/Nacional) el 22–23/jul |
| Duplicados | **No** (`DUP_DN=0`) |
| Fuera del alcance | **No** (NY 10:30 / NY 2:30 / Leidsa / Nacional están en las 7) |
| Diferencia de consulta | **No** (SQL idéntica; 120 ⊆ 122) |
| Inconsistencia de base | **Parcial / sync asimétrico:** DEV adelantado en NY family; PROD adelantado en Nacional/Leidsa/Loteka |

---

## Documentación de cambio de dataset (baseline)

| Ambiente | Total 35+14 official-scope | Baseline |
|----------|----------------------------|----------|
| PROD Beta 2.1 (medido 2026-07-29) | **120** | Certificado previo |
| DEV Workspace MVP (medido 2026-07-29) | **122** | **Nuevo baseline DEV** = 120 PROD + `2026-07-22` + `2026-07-23` |

Cuando PROD sincronice New York 10:30/2:30 (y el 35 de esos días), se espera que PROD pase a **122** (salvo que esos números se corrijan en origen).

---

## Artefactos

- `dev_raw.tsv` / `prod_raw.tsv`
- `diff_summary.json`
- `dev_jul22_23_draws.tsv` / `prod_jul22_23_draws.tsv`
- Este archivo: `DIAGNOSIS_120_vs_122.md`
