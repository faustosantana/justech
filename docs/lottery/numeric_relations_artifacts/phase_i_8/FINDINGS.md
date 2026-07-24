# I-8 Hallazgos — Producción

## Crítico
_Ninguno._

## Alto
_Ninguno pendiente._

## Medio
1. **API `lottery_names` en multi-lotería:** en respuesta API de analyze N=45 Leidsa+Loteka, un elemento de `lottery_names` llegó como UUID en lugar del nombre humano. La UI muestra correctamente `Quiniela Leidsa, Quiniela Loteka`. No corrige metodología; mejora de serialización pendiente.
2. **Chat multi (caso F):** ante «Analiza el 45 en Leidsa y Loteka…» el asistente respondió analizando el 26 en una corrida de evidencia. HTTP 200 y disclaimer correctos; posible desvío de interpretación LLM (no se toca prompt activo en I-8).
3. **Etiqueta UI «Draw IDs analizados»:** muestra el *conteo* de ocurrencias usadas, no la lista de `draw_id`. Los `draw_id` sí existen en metadata/traza expandible (Auditoría). Mejora de copy.
4. **Frontend logs `Failed to find Server Action "fk"`:** ruido post-redeploy (cache de cliente/versión Next). Sin impacto funcional en Control Center; ERR_S/ERR_B=0 en ventana de monitoreo.

## Bajo
1. Truncado del título de app en sidebar (`Resultados de L…`) — layout preexistente de la app Loterías.
2. Primera captura local de Tabla 1 a 1.5s mostró «Cargando…»; con espera ≤25s carga completa (no hang).

## Mejora UX
1. Scroll automático al bloque Resultado/Ranking tras «Analizar relaciones».
2. Resaltar loterías seleccionadas fuera del viewport del checklist.
3. Vacío de grupo/código en filas sin grupo: ya muestra estado vacío implícito; podría decir «sin grupo».

## Correcciones aplicadas en I-8
1. Smoke OpenAPI: URL corregida a `http://127.0.0.1:8000/openapi.json` (no bajo `/api/v1`). Re-smoke **27 PASS / 0 FAIL** (suite I-8 ampliada; el caso OpenAPI que fallaba en I-7 queda PASS).
2. Ningún fix de producto crítico/alto requerido tras validación visual VPS.

## Pendientes (fuera de alcance I-8)
- Normalizar `lottery_names` en API multi.
- Observabilidad del desvío chat N observado.
- Copy «Draw IDs analizados» → «Ocurrencias analizadas» + enlace a trazas.
