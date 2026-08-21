# Histórico de adjudicaciones DGCP — Inteligencia 360°

## Fuentes

- API DGCP `GET /contratos` y `GET /contratos/articulos`
- Índice local `dgcp_historical_awards` (sin segundo repositorio)
- Caché similar: `dgcp_process_historical_similar_results` (flujo previo)

## Reglas

- **Última compra** = última **adjudicación/contrato válido** por `award_date` (no última publicación).
- Estados inválidos excluidos: cancelada, desierta, anulada, etc.
- Montos del proceso actual = **estimados**; históricos = **adjudicados/contratados**.
- Clasificación: `EXACTA` | `ALTA_SIMILITUD` | `RELACIONADA` (nunca “última compra” si solo es similar).
- Sin LLM para cifras; el resumen ejecutivo solo redacta métricas calculadas.
- Proveedor: RPE en índice; RNC solo si viene en payload fuente.

## API

```
GET /api/v1/dgcp/processes/{id}/historical-intelligence?window_months=24
```

Ventanas: `12` | `24` | `36` | `0` (todo).

Legacy (sin romper):

```
GET/POST …/historical-similar
POST /historical-awards/index
GET  /historical-awards/stats
```

## UI

Pestaña **Inteligencia histórica** en detalle de licitación:

1. Tarjetas: Última compra · Proveedor reciente · Precio · Procesos similares  
2. Tabs: Resumen · Compras · Proveedores · Productos · Precios · Relacionados  

## Performance

Consulta el índice local (sin matching pesado a la API en cada carga).  
Reindexación institucional bajo demanda vía `POST /historical-awards/index`.
