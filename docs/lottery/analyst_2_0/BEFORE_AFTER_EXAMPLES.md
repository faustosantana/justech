# BEFORE_AFTER_EXAMPLES

## Caso A — Loterías del evento

**Usuario T1:** ¿Cuándo fue la última vez que salió el 78 y el 02 el mismo día?

| | Antes | Después (2.0) |
|--|-------|----------------|
| T2 «¿En cuáles loterías?» | «No pude completar la consulta…» o last_n de un solo número | Respuesta del **evento**: loterías/posiciones de 78 y 02; sujetos conservados; `same_day` intacto |
| Hermes | N/A | `attribute_of_last_event` + `reuse_evidence` si ya hay apariciones |
| Jerga | posible | prohibida (`same_day`, `metric`, etc.) |

## Caso B — Posiciones

**T3:** ¿Y en qué posiciones?  
→ Mismo evento; posiciones concretas (`1ra`/`2da`/`3ra`), no «todas las posiciones» como fila.

## Caso C — Anteriores

**T4:** ¿Cuáles fueron las 3 coincidencias anteriores?  
→ Lista de coincidencias del par, no apariciones individuales.

## Caso D — TTL

Sesión activa a 9 min → contexto válido.  
Sin actividad 10+ min → no reutilizar sticky same_day en silencio.
