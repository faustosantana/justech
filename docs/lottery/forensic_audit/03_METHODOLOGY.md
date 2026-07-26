# 03 — Metodología forense

## Principios

1. Solo histórico oficial FEATURED_SEVEN.
2. Solo metodología vigente `nr-historical-relations-j1.0.0`.
3. Sin mirada al futuro al formar el fuerte.
4. Validación **solo** en los siete días siguientes.
5. Si el fuerte no sale: investigar **qué sí salió** y su distancia matemática.

## Paso A — Día de análisis (sin futuro)

Para cada fecha con ≥2 números observados (primer número in-universe 1..100 por lotería):

```
Número observado
    ↓
Tabla 1 → candidatos
    ↓
Tabla 2 → confirmadores
    ↓
Si un confirmador está entre los otros observados
    ↓
Fuerte oficial = candidato Tabla 1
```

Reglas inmutables:

- el confirmador **nunca** se fortalece;
- vecino T2 directo sin paso T1 **no** es fuerte oficial.

## Paso B — Ventana de evidencia

```
Día D (análisis)     → forma fuertes (sin mirar D+1…)
Días D+1 … D+7       → observa apariciones reales
Día D                → NUNCA se usa para validar
```

Para cada aparición se registra: día, lotería, posición, referencia.

## Paso C — Distancia al fuerte

| Distancia | Etiqueta | Significado |
|----------:|----------|-------------|
| 0 | FUERTE_EXACTO | Salió el fuerte |
| 1 | COMPANERO_TABLA1 | Compañero del grupo T1 |
| 2 | MISMO_CODIGO_T1 | Mismo código T1 (reserva; suele colapsar en 1) |
| 3 | VECINO_TABLA2 | Vecino T2 del fuerte |
| 4 | RELACION_INDIRECTA | Un salto vía compañero o vecino |
| 5 | SIN_RELACION | Ninguna de las anteriores |

Por activación se guarda la **distancia mínima** a cualquier número de la ventana.

## Paso D — Control de azar (imparcialidad)

Para cada activación se simula un “fuerte” aleatorio 1..100 con su propia familia T1
y se mide si aparece en **la misma ventana**. El lift = tasa_motor / tasa_azar.

Sin este control, una tasa cruda alta en una ventana densa se malinterpreta como ventaja.
