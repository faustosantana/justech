# 01 — Resumen ejecutivo

Esta fase reconstruye el método del socio frente al motor oficial y describe
cómo se mueven las familias T1 después de cada fuerte.

## Casos manuales

| Caso | Manual | Oficial | Clase | Certeza |
| --- | --- | --- | --- | --- |
| M1 | 29 | [29] | FUERTE_OFICIAL_UNICO | ALTA |
| M2 | 75 | [] | VECINO_T2_DIRECTO | ALTA |
| M3 | 35 | [22, 35] | FUERTE_OFICIAL_ENTRE_VARIOS | ALTA |
| M4 | 54 | [54] | FUERTE_OFICIAL_UNICO | ALTA |
| M5 | 94 | [94] | FUERTE_OFICIAL_UNICO | ALTA |

## Hallazgos clave

1. **M1 / M4** se reproducen como fuerte oficial único.
2. **M3** es oficial entre varios (35 y 22); el socio eligió 35 (más confirmadores).
3. **M2 (75)** es **VECINO_T2_DIRECTO** — no incorporar.
4. **M5**: tanto `39+58→94` como `39+84→94` son oficiales; 58 y 84 comparten grupo T2 con 94.
5. Dinámica −1: tasa 77.54% · −1 funciona principalmente como destino frecuente de la familia (tasa 77.54%). En 393 activaciones −1 apareció antes que el fuerte (puente/precursor). En 286 casos −1 precedió a −2. Fue el confirmador original en 0 activaciones.
6. Misses: 552 con compañero T1 en 507.

No se inicia J-11A. No se modifica el motor.
