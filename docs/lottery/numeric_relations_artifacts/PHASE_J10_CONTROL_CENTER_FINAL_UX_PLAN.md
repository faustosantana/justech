# J-10 — Rediseño final del Control Center de Inteligencia Numérica

**Estado:** EN CURSO (DEV only)  
**Baseline:** tag `nr-number-visual-explorer-j9-dev-approved` @ `1d1da49`  
**Rama:** `feature/nr-control-center-final-ux-j10`  
**Producción:** prohibida hasta autorización expresa post–J-10  

---

## 1. Objetivo

Un solo Control Center usable: ver resultados recientes de **siete loterías destacadas**, hacer clic en un número y abrir de inmediato el **expediente** (J-9), con herramientas técnicas (T1/T2/grupos/relaciones/auditoría) rediseñadas y subordinadas.

## 2. Garantías (inmutables)

- No modificar fórmulas, Tabla 1, Tabla 2, histórico, `/analyze` v1
- Reutilizar J-1→J-9
- Solo DEV · `production_forbidden` · no deploy Prod

## 3. Decisiones de producto

| Decisión | Detalle |
|----------|---------|
| Alcance principal | Solo loterías `is_featured=true` (objetivo: **7**) |
| Fuera del principal | Anguila, Haití, Miami/Florida/NY — siguen en administración |
| Clic en número | Abre expediente inmediato (Historial del Número / caso) |
| Orden del expediente | condición → candidato → confirmadores → explicación → 7 sorteos → historial → señales |
| Conservar | T1, T2, Agrupaciones T1/T2, Relaciones, Auditoría (rediseñadas, después del análisis) |
| Nav | Menos botones técnicos; herramientas profundas solo admin |

## 4. Set canónico DEV de 7 destacadas

Como DEV tenía `is_featured=false` en todas, J-10 siembra (solo DEV) este set:

1. Quiniela Leidsa  
2. Quiniela Loteka  
3. Loteria Nacional  
4. Loto Leidsa  
5. Quiniela Real  
6. Loto Real  
7. Gana Mas  

Fuente de verdad UI: flag `is_featured` (no hardcode de nombres en runtime salvo seed/admin).

## 5. Fases de implementación

| Fase | Entrega |
|------|---------|
| J-10.0 | Tag baseline + rama + este plan |
| J-10.1 | Hub Inteligencia: 7 destacadas + últimos resultados + clic → expediente |
| J-10.2 | Expediente-first (query params, orden visual, señales) |
| J-10.3 | Rediseño T1/T2/grupos/relaciones/auditoría (secundario) |
| J-10.4 | Nav limpia + permisos |
| J-10.5 | E2E, capturas, perf vs baseline J-9, veredicto |

## 6. Criterio de despliegue final

Solo después de J-10 completo: E2E, metodología, 7 loterías, clic/expediente, señales, tablas rediseñadas, auditoría, móvil, permisos, rendimiento, capturas, Prod intacta.

**No desplegar Prod sin nueva autorización.**
