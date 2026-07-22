# Histórico similar DGCP — búsqueda bajo demanda

## Enfoque

**No hay indexación masiva.** JAIOS consulta la API DGCP solo cuando el usuario lo solicita, con límite estricto de páginas (3 × 50 ítems) y filtrado por institución + palabras clave.

## Cuándo se habilita

- Oportunidad en estado: `interested`, `to_bid`, `won`, `lost`
- El usuario pulsa **«Buscar histórico de compras similares»** en la pestaña Histórico
- Opcional: **Actualizar** para forzar nueva consulta (invalida caché)

## API

```
GET  /api/v1/dgcp/processes/{id}/historical-similar          # lee caché
POST /api/v1/dgcp/processes/{id}/historical-similar/search   # búsqueda on-demand
```

Alias: `/opportunities/{id}/historical-similar`

### POST body

```json
{
  "refresh": false,
  "limit": 3,
  "extra_query": "toner HP opcional"
}
```

## Caché

Tabla `dgcp_process_historical_similar_results`:
- Una fila por proceso (`opportunity_id`)
- TTL: 72 horas
- Campos: keywords, resultados JSON, páginas escaneadas, errores

## Fuentes DGCP (consulta limitada)

| Endpoint | Uso on-demand |
|----------|---------------|
| `GET /contratos` | Proveedor, monto, institución, fecha |
| `GET /contratos/articulos` | Descripción ítem, precio unitario, cantidad |

Máximo **3 páginas** por búsqueda — sin jobs largos ni cron.

## Motor de similitud

- Misma institución compradora (match flexible)
- Palabras clave del título, descripción, objeto, ítems del proceso
- Sinónimos: toner/cartucho/tinta, HP/Canon/Lexmark, laptop/portátil, etc.
- Top 3 resultados por defecto (hasta 10 en «Ver más»)

## UI

Pestaña **Histórico** en detalle de licitación:
- Botón de búsqueda manual
- Tabla con últimas 3 compras similares
- Recomendación de precio e insights IA

## Desactivado

- `POST /historical-awards/index` — eliminado
- `index_historical` en sync DGCP — eliminado
- Indexación masiva de `dgcp_historical_awards` — no se usa en flujo operativo

## Desarrollo local

```bash
docker compose exec backend alembic upgrade head
# Marcar interés en una licitación → pestaña Histórico → Buscar
```

## Pendientes producción

1. Migración `034_dgcp_historical_similar_cache`
2. Validar rate limits DGCP en uso real
3. Ajustar `MAX_PAGES` si hace falta más cobertura (con cuidado)
4. No desplegar hasta QA con procesos reales de interés
