# Performance — Justech e-CF (justech_dev)

**Fecha:** 2026-07-12 UTC  
**Host:** erp.justech.do (VPS JAIOS)  
**Alcance:** generación XML local + firma stub + envío mock + commit  
**NO afirma soporte para 1,000,000 documentos.**

## Resultados

| Volumen | Duración (s) | Throughput (docs/s) | max RSS (KB) | Δ RSS (KB) |
|---|---:|---:|---:|---:|
| 100 | 1.776 | 56.31 | 222596 | 0 |
| 1,000 | 19.248 | 51.95 | 225668 | 3072 |
| 10,000 | 154.486 | 64.73 | 267012 | 41344 |

## Observaciones

- Entorno de desarrollo compartido; métricas no son SLA de producción.
- Envío DGII = **mock** (sin red DGII).
- Consultas SQL / locks: sin deadlocks observados; GL unbalanced = 0 post-bench.
- Jobs fallidos / dead-letter: 0 en corrida mock de bench.
- Duplicados: recepción detecta duplicado por hash (smoke RECEIVE DUP=True).

## Conclusión

Soportado y medido hasta **10,000** documentos en este entorno.  
Escalas superiores requieren benchmark dedicado y capacidad de hardware/BD.
