# Fase 5.2 — Dashboard Lottery IA + congelamiento Motor v1.0

## Objetivo

Dar visibilidad al estado del sistema y registrar oficialmente el **Motor v1.0 congelado**.  
Esta fase **no** agrega reglas matemáticas nuevas.

## Dashboard (`/lottery/ia`)

Reutiliza Resultados (oficial), Piloto prospectivo y artefactos de tiebreak. Tarjetas:

| Bloque | Campos |
|--------|--------|
| **Motor** | Estado, Versión, Perfil activo, Tiebreak, Fecha de congelamiento, Commit (solo lectura) |
| **Resultados** | Última actualización, Total sorteos, Total loterías, Pendientes por sincronizar |
| **Piloto** | Predicciones LOCKED, Evaluadas, Pendientes |
| **Rendimiento** | Top 1, Top 2, Multi-Fuerte (desde `artifacts/tiebreak/final_benchmark.json`) |
| **Último sorteo** | Lotería, Fecha, Resultado, Predicción, Estado (Correcto / Incorrecto / Pendiente) |

API (solo lectura):

- `GET /lottery/ia/dashboard`
- `GET /lottery/ia/motor-freeze`

## Motor v1.0 congelado

| Campo | Valor |
|-------|--------|
| Motor Version | **1.0** |
| Estado | FROZEN |
| Perfil activo | `socio` (`OPERATIONAL_RANKING_PROFILE`) |
| Tiebreak activo | `TIEBREAK_PROFILE_SOCIO_V1+EMPATE_MULTI_FUERTE` |
| Fecha de congelamiento | 2026-07-26 |
| Commit | `git rev-parse --short HEAD` al consultar |
| UI editable | **No** |

Registro: `analysis_engine/motor_v1_freeze.py`  
Artefacto: `artifacts/motor_freeze/motor_v1_freeze.json`

## Mejoras UX — Tabla 1 y Tabla 2

Componente compartido `motor-table.tsx` (ambas tablas):

- Eliminadas columnas **Número** y **Cantidad** de la grilla principal.
- Se mantienen buscadores: **Buscar número**, **Buscar código**.
- Orden fijo por **Código** (ascendente).
- Los (hasta) 100 registros se muestran en **una sola página** — sin paginación.
- El número de referencia sigue disponible en el panel de detalle.

## No modificado

- Motor (fórmulas / ranking / tiebreak / J-11A).
- Tabla 1 / Tabla 2 (catálogo matemático).
- Producción (`production_modified: false`).

## Pruebas

`backend/tests/lottery/dashboard/test_fase52_dashboard.py`
