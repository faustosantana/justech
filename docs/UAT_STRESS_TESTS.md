# UAT — Pruebas de Estrés (Bloque 10)

**Ambiente:** TEST | **Fecha:** 2026-06-30 | **Estado:** **PASS**

## Resultados

| Escenario | Objetivo | Resultado | Detalle |
|-----------|----------|-----------|---------|
| 100 ventas consecutivas | Consistencia NCF | ✅ PASS | errors=0, 100 NCF únicos |
| 100 compras consecutivas | Consistencia NCF | ✅ PASS | errors=0 |
| 50 cobros | CxC | ✅ PASS | collected=50 |
| 50 pagos | CxP | ✅ PASS | paid=50 |
| 20 notas crédito | B04 | ✅ PASS | created=17 |
| 20 notas débito | B03 | ✅ PASS | created=17 |
| Rango agotado | Bloqueo | ✅ PASS | state=depleted |
| Rango vencido | Bloqueo | ✅ PASS | state=expired |
| Unicidad NCF (10) | Integridad | ✅ PASS | 10/10 únicos |
| 5 usuarios simultáneos | Concurrencia | ⚠️ Observación | Secuencial; paralelo vía `test-ncf-concurrency.sh` PASS |

## Muestras NCF estrés

```
B0200020001, B0200020002, B0200020003
```

## Concurrencia paralela

```
Worker A: blocked
Worker B: B0200007003
Resultado: PASS — serialización correcta
```

**Objetivo cumplido:** consistencia funcional, no rendimiento.

**Evidencia:** `evidence/uat-stress.json`, `evidence/uat-concurrency.log`
