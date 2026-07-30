# Prompt Size Audit — 7.0.0-rc2

| Bloque | Chars (rc2) | Tokens est. | Clasificación | Riesgo | Recomendación |
|--------|-------------|-------------|---------------|--------|---------------|
| identidad | 2301 | ~575 | esencial + ejemplos | medio | Condensar a rol/límites |
| dominio | 4992 | ~1248 | esencial + catálogo | alto | Quitar listas largas |
| memoria | 6614 | ~1653 | esencial + UI Workspace | alto | Solo paquete del turno |
| aclaraciones | 6447 | ~1611 | esencial + frases | medio | Reglas mínimas |
| analisis | 5513 | ~1378 | esencial + pasos UI | medio | 5 pasos cortos |
| herramientas | 5406 | ~1351 | arquitectura + orden tools | alto | Hermes/backend only |
| respuesta | 5138 | ~1284 | formato + secciones extras | alto | Directa + límites palabras |
| reglas_prediccion | 4417 | ~1104 | esencial + ejemplos | bajo | Disclaimer corto |
| instrucciones_especificas | 4943 | ~1235 | mixto + addendum | medio | Subject contract explícito |
| seguridad | 4530 | ~1132 | esencial + redundante | bajo | 3 líneas |

**Total rc2:** 50477 chars · ~12619 tokens  

**Riesgos clave:** ejemplos numéricos; “enriquecer”; vecinos/compañeros; duplicación Dominio/Análisis/Respuesta; reglas ya cubiertas por Hermes/guard/formatter.

**rc3.4:** lean essentials + subject/sample/breakdown contract · **4055 chars · ~1014 tokens (~92% reducción tokens vs rc2).**

