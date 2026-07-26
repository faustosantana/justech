# 19 — Conclusiones finales (solo evidencia)

## Las 10 preguntas

### 1. ¿Qué ocurre realmente después de un fuerte?

En la ventana D+1…D+7, el número fuerte aparece en **75.16%**
de las activaciones. Si no, casi siempre aparece un compañero T1
(**91.85%** de los misses).
La misma ventana también hace aparecer un número aleatorio al **75.02%**.

### 2. ¿El fuerte suele salir?

Sale con frecuencia cruda alta (**75.16%**).
Respecto al azar en 7 días: **no más** (lift **1.0018**).

### 3. ¿O suelen salir números relacionados?

En crudo, sí (familia **97.97%**).
Respecto al azar: lift familia **1.0032**.

### 4. ¿Qué relación matemática aparece con mayor frecuencia?

Entre misses: **compañero Tabla 1**.
En el conjunto total: **fuerte exacto** (dist 0), seguido de compañero (dist 1).

### 5. ¿Qué tabla aporta más información?

- **Para crear el fuerte:** Tabla 2 (confirmación) es necesaria.
- **Para clasificar lo que sale después:** Tabla 1 (familia) domina los misses.
- **Para ventaja vs azar en 7d:** ninguna muestra lift relevante.

### 6. ¿Cuál es la verdadera utilidad de Tabla 1?

Mapear **familias** de números alrededor de un candidato. Útil como lenguaje
descriptivo; no como prueba de elevación 7d.

### 7. ¿Cuál es la verdadera utilidad de Tabla 2?

**Confirmar** candidatos T1. Como “número que sale en lugar del fuerte”,
es secundaria frente a compañeros T1.

### 8. ¿Las tablas describen un número o una familia?

**Una familia con centro.** El fuerte es el centro declarado; la evidencia de misses
se concentra en compañeros del mismo grupo T1.

### 9. ¿Existe una estructura matemática más profunda?

La estructura medida aquí es: **geometría T1×T2 + saturación de ventana 7d**.
El patrón miss→compañero es real en crudo y, a la vez, compatible con azar bajo
densidad alta. No se introduce una fórmula nueva.

### 10. Si se rediseñara el motor solo con esta evidencia…

| Conservar | Descartar como señal 7d | Investigar más |
|-----------|-------------------------|----------------|
| Geometría T1×T2 para proponer/confirmar | Usar “salió en 7 días” como métrica de éxito predictivo | Ventanas más cortas (1–3d) con baseline same-k |
| Distancia 0–5 como lenguaje de explicación | DIRECT_T2 como fuerte | Seguimiento de familia vs exacto con controles |
| FEATURED_SEVEN como universo | Prometer lift en ventana ancha | Comparar generadores/confirmadores con tests fuera de muestra |

## Veredicto forense (imparcial)

> Tras un fuerte oficial, el histórico de 7 años en ventana +1…+7 muestra
> co-ocurrencias frecuentes del exacto y de su familia T1.
> Esas co-ocurrencias **no exceden** de forma material lo esperado por azar
> dada la densidad de la ventana (lift ≈ 1.00).
>
> Las tablas describen familias. La ventana de 7 días no discrimina.
