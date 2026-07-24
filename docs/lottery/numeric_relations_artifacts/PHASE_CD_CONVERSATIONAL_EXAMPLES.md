# Ejemplos conversacionales — Motor de Relaciones Numéricas

## 1. Completo (una lotería, últimas 10)

**Usuario:** Analiza el 26 en las últimas 10 veces que salió en Leidsa.

**Intent:** `lottery_analyze_numeric_relations`  
`observed_number=26`, `lotteries=[Leidsa]`, `occurrence_mode=last_k`, `occurrence_k=10`

**Respuesta (plantilla, hechos del motor):** narración con compañeros, ranking, disclaimer de señal histórica.

## 2. Compañeros más fuertes (pide límite)

**Usuario:** ¿Cuáles compañeros están más fuertes cuando sale el 34?

**Sistema:** clarifica lotería y cantidad (5 / 10 / 20 / todas). No inventa.

## 3. Vecinos últimas 20

**Usuario:** Busca las últimas 20 veces que salió el 18 y revisa sus vecinos.

**Sistema:** pide lotería (falta imprescindible).

## 4. Multi-lotería

**Usuario:** Analiza el 45 en Leidsa y Loteka con las últimas 20 veces.

**Intent:** tool con 2 loterías, `occurrence_k=20`.

## 5. Todas las ocurrencias

**Usuario:** Muéstrame todas las ocurrencias disponibles del 26 en Leidsa.

**Intent:** `occurrence_mode=all`.

## 6. Sin resultados (Huawei no inventa)

Cuando el motor devuelve `occurrences_used=0`:

```text
… No encontré ocurrencias históricas donde saliera ese número,
así que no hay compañeros fortalecidos ni ranking que reportar.
No invento compañeros, códigos, vecinos ni puntuaciones.
Esto es una señal histórica del método, no una certeza ni garantía.
```

## 7. Ejemplo controlado (ambiente de pruebas)

Número observado: **26**  
Compañeros: **27**, **38**  
27 → T2 **53**, vecinos **68, 76, 92** → si los tres aparecen en el sorteo ancla → **score 3**  
Ranking: 1) 27 — 3 · 2) 38 — 0
