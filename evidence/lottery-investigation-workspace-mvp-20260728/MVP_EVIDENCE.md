# Investigation Workspace MVP — evidencia DEV

Generado: 2026-07-29T01:26:04.460631+00:00
DB: `jaios_lottery_dev@5433`

## Turnos

### T1: ¿Cuántas veces coincidieron el 35 y el 14 el mismo día?
- total: **122** (items SQL: 122)

### T2: Muéstrame esos resultados
- Hermes turn_type: `asset_action` reason=`show_results`
- requires_research: `False` reasoning_mode=`skip`
- action: `show_results` row_count=`122`
- filters: `{}` sort: `{'field': 'fecha', 'direction': 'desc'}`

```
Tabla de coincidencias same-day (35 y 14): 122 fila(s).
Orden: fecha desc.

| fecha | loteria | numero_a | posicion_a | numero_b | posicion_b | tipo_coincidencia |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-07-23 | New York 10:30 | 35 | 1ra posición | 14 | 2da posición | misma_fecha |
| 2026-07-22 | New York 2:30 | 35 | 1ra posición | 14 | 2da posición | misma_fecha |
| 2026-07-20 | Loteria Nacional | 35 | 1ra posición | 14 | 2da posición | misma_fecha |
| 2026-06-23 | Loteria Nacional | 35 | 1ra posición | 14 | 1ra posición | misma_fecha |
| 2026-05-29 | Quiniela Loteka | 35 | 3ra posición | 14 | 2da posición | misma_fecha |
| 2026-04-17 | Quiniela Real | 35 | 3ra posición | 14 | 2da posición | misma_fecha |
| 2026-03-07 | Quiniela Loteka | 35 | 2da posición | 14 | 3ra posición | misma_loteria |
| 2026-03-06 | New York 2:30 | 35 | 2da posición | 14 | 3ra posición | misma_fecha |
| 2026-02-02 | Loteria Nacional | 35 | 1ra posición | 14 | 2da posición | misma_fecha |
| 2026-01-23 | New York 10:30 | 35 | 3ra posición | 14 | 3ra posición | misma_fecha |
| 2025-12-14 | New York 2:30 | 35 | 1ra posición | 14 | 1ra posición | misma_fecha |
| 2025-10-27 | Quiniela Leidsa | 35 | 1ra posición | 14 | 2da posición | misma_fecha |
| 2025-10-20 | Quiniela Real | 35 | 2da posición | 14 | 2da posición | misma_fecha |
| 2025-08-22 | Gana Mas | 35 | 1ra posición | 14 | 1ra posición | misma_fecha |
| 2025-08-15 | Quiniela Leidsa | 35 | 3ra posición | 14 | 1ra posición | misma_fecha |
| 2025-08-08 | Quiniela Real | 35 | 3ra posición | 14 | 1ra posición | misma_fecha |
| 2025-08-04 | Gana Mas | 35 | 2da posición | 14 | 1ra posición | misma_loteria |
| 2025-06-27 | Quiniela Real | 35 | 1ra posición | 14 | 3ra posición | misma_fecha |
| 2025-05-18 | Quiniela Leidsa | 35 | 3ra posición | 14 | 1ra posición | misma_fecha |
| 2025-04-20 | Quiniela Loteka | 35 | 3ra posición | 14 | 3ra posición | misma_fecha |

Controles: Ver tabla · Filtrar · Ordenar · Exportar Excel · Ver resumen · Ver más
```

### T3: Filtra solo Loteka
- Hermes turn_type: `asset_action` reason=`filter_lottery`
- requires_research: `False` reasoning_mode=`skip`
- action: `filter_results` row_count=`28`
- filters: `{'lottery': 'Loteka'}` sort: `{'field': 'fecha', 'direction': 'desc'}`

```
Filtré la tabla a «Loteka»: 28 fila(s).
Filtros activos: {'lottery': 'Loteka'}.
Orden: fecha desc.

| fecha | loteria | numero_a | posicion_a | numero_b | posicion_b | tipo_coincidencia |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-07-20 | Loteria Nacional | 35 | 1ra posición | 14 | 2da posición | misma_fecha |
| 2026-06-23 | Loteria Nacional | 35 | 1ra posición | 14 | 1ra posición | misma_fecha |
| 2026-05-29 | Quiniela Loteka | 35 | 3ra posición | 14 | 2da posición | misma_fecha |
| 2026-04-17 | Quiniela Real | 35 | 3ra posición | 14 | 2da posición | misma_fecha |
| 2026-03-07 | Quiniela Loteka | 35 | 2da posición | 14 | 3ra posición | misma_loteria |
| 2025-10-20 | Quiniela Real | 35 | 2da posición | 14 | 2da posición | misma_fecha |
| 2025-04-20 | Quiniela Loteka | 35 | 3ra posición | 14 | 3ra posición | misma_fecha |
| 2025-03-17 | Loteria Nacional | 35 | 2da posición | 14 | 3ra posición | misma_fecha |
| 2024-01-23 | Quiniela Loteka | 35 | 2da posición | 14 | 1ra posición | misma_fecha |
| 2024-01-21 | Quiniela Loteka | 35 | 1ra posición | 14 | 1ra posición | misma_fecha |
| 2021-07-11 | Loteria Nacional | 35 | 2da posición | 14 | 3ra posición | misma_fecha |
| 2020-10-22 | Quiniela Loteka | 35 | 2da posición | 14 | 1ra posición | misma_loteria |
| 2020-03-17 | Quiniela Leidsa | 35 | 2da posición | 14 | 2da posición | misma_fecha |
| 2019-07-05 | Quiniela Loteka | 35 | 3ra posición | 14 | 3ra posición | misma_fecha |
| 2019-05-19 | New York 2:30 | 35 | 3ra posición | 14 | 2da posición | misma_fecha |
| 2019-04-23 | Quiniela Loteka | 35 | 3ra posición | 14 | 1ra posición | misma_fecha |
| 2019-03-31 | Quiniela Loteka | 35 | 3ra posición | 14 | 1ra posición | misma_fecha |
| 2018-10-10 | New York 10:30 | 35 | 2da posición | 14 | 2da posición | misma_fecha |
| 2018-08-21 | Quiniela Loteka | 35 | 1ra posición | 14 | 2da posición | misma_loteria |
| 2018-07-26 | Quiniela Loteka | 35 | 3ra posición | 14 | 2da posición | misma_fecha |

Controles: Ver tabla · Filtrar · Ordenar · Exportar Excel · Ver resumen · Ver más
```

### T4: Ordénalos por fecha
- Hermes turn_type: `asset_action` reason=`sort_results`
- requires_research: `False` reasoning_mode=`skip`
- action: `sort_results` row_count=`28`
- filters: `{'lottery': 'Loteka'}` sort: `{'field': 'fecha', 'direction': 'desc'}`

```
Ordené por fecha (desc). 28 fila(s).
Filtros activos: {'lottery': 'Loteka'}.
Orden: fecha desc.

| fecha | loteria | numero_a | posicion_a | numero_b | posicion_b | tipo_coincidencia |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-07-20 | Loteria Nacional | 35 | 1ra posición | 14 | 2da posición | misma_fecha |
| 2026-06-23 | Loteria Nacional | 35 | 1ra posición | 14 | 1ra posición | misma_fecha |
| 2026-05-29 | Quiniela Loteka | 35 | 3ra posición | 14 | 2da posición | misma_fecha |
| 2026-04-17 | Quiniela Real | 35 | 3ra posición | 14 | 2da posición | misma_fecha |
| 2026-03-07 | Quiniela Loteka | 35 | 2da posición | 14 | 3ra posición | misma_loteria |
| 2025-10-20 | Quiniela Real | 35 | 2da posición | 14 | 2da posición | misma_fecha |
| 2025-04-20 | Quiniela Loteka | 35 | 3ra posición | 14 | 3ra posición | misma_fecha |
| 2025-03-17 | Loteria Nacional | 35 | 2da posición | 14 | 3ra posición | misma_fecha |
| 2024-01-23 | Quiniela Loteka | 35 | 2da posición | 14 | 1ra posición | misma_fecha |
| 2024-01-21 | Quiniela Loteka | 35 | 1ra posición | 14 | 1ra posición | misma_fecha |
| 2021-07-11 | Loteria Nacional | 35 | 2da posición | 14 | 3ra posición | misma_fecha |
| 2020-10-22 | Quiniela Loteka | 35 | 2da posición | 14 | 1ra posición | misma_loteria |
| 2020-03-17 | Quiniela Leidsa | 35 | 2da posición | 14 | 2da posición | misma_fecha |
| 2019-07-05 | Quiniela Loteka | 35 | 3ra posición | 14 | 3ra posición | misma_fecha |
| 2019-05-19 | New York 2:30 | 35 | 3ra posición | 14 | 2da posición | misma_fecha |
| 2019-04-23 | Quiniela Loteka | 35 | 3ra posición | 14 | 1ra posición | misma_fecha |
| 2019-03-31 | Quiniela Loteka | 35 | 3ra posición | 14 | 1ra posición | misma_fecha |
| 2018-10-10 | New York 10:30 | 35 | 2da posición | 14 | 2da posición | misma_fecha |
| 2018-08-21 | Quiniela Loteka | 35 | 1ra posición | 14 | 2da posición | misma_loteria |
| 2018-07-26 | Quiniela Loteka | 35 | 3ra posición | 14 | 2da posición | misma_fecha |

Controles: Ver tabla · Filtrar · Ordenar · Exportar Excel · Ver resumen · Ver más
```

### T5: Exporta a Excel
- Hermes turn_type: `asset_action` reason=`export_xlsx`
- requires_research: `False` reasoning_mode=`skip`
- action: `export_results` row_count=`28`
- filters: `{'lottery': 'Loteka'}` sort: `{'field': 'fecha', 'direction': 'desc'}`
- download: `/api/v1/lottery/workspace/exports/ws_4a09a51084ad42a8_c35048e483.xlsx/download` file=`workspace-35-14-4a09a510.xlsx` storage=`ws_4a09a51084ad42a8_c35048e483.xlsx`

```
Exportación lista: **workspace-35-14-4a09a510.xlsx** (28 fila(s)).

Filtros: {'lottery': 'Loteka'}.
Orden: {'field': 'fecha', 'direction': 'desc'}.

Descarga: /api/v1/lottery/workspace/exports/ws_4a09a51084ad42a8_c35048e483.xlsx/download
```
