# Regla seleccionada

## Operativa

`TIEBREAK_PROFILE_SOCIO + EMPATE_MULTI_FUERTE`  
ID: `TIEBREAK_PROFILE_SOCIO_V1`

## Jerarquía (mínima, validada)

1. Preferir candidatos cuyo T1 incluya la **primera observación** (generator-first).
2. Más fuentes observadas independientes (unión T1∪T2).
3. Más confirmadores T2 directos.
4. Más fuentes T1 directas.
5. Flag de soporte cruzado T1×T2.
6. Si las claves siguen iguales → **no inventar ganador** → `EMPATE_MULTI_FUERTE`.

## Qué no se usa

- Orden lexicográfico por número.
- Diferencias espurias de `total_path_count` / profundidad de paths cuando la estructura T1×T2 es idéntica.
- Condiciones hardcodeadas por fecha o por caso M1–M5 / 14 errores.
- Labels futuros.

## Umbral de empate práctico

`DEFAULT_PRACTICAL_THRESHOLD = 0.0`

## Relación con top-1 / top-2

- Top-1 mejora en subtipo role-swap.
- Subtipo estructural idéntico no cuenta como top-1 falso; el histórico permanece en top-2 / multi-fuerte.
