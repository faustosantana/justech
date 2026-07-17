# P0.1 — Decisión de arquitectura

## Alternativa seleccionada: **B (adaptada)**

**Justech = SoT de emisión**  
**LATAM = SoT de entrada en compras recibidas**  
**FDP = API canónica de lectura** (no almacén nuevo)

### Por qué

1. Emisión ya consume solo rangos Justech; Adel está congelado (`adel_freeze`).
2. Reportes/PDF ya leen vía FDP con prioridad Justech→LATAM.
3. Compras recibidas deben conservar el NCF del proveedor en campos LATAM (realidad DGII 606).
4. Crear columnas “neutrales” (C) añade migración sin eliminar writers duales.
5. Volver a LATAM como SoT de emisión (A) reabre riesgo Adel y deshace motor Justech.

## Alternativas descartadas

| Opción | Motivo de descarte |
|---|---|
| A — LATAM SoT | Lucha con adel_freeze; segunda secuencia; upgrades frágiles |
| C — almacén canónico nuevo | Costo alto; FDP ya es fachada; no resuelve dual-write solo |

## Ventajas

- Cambio mínimo (flag + gate).
- Históricos LATAM-only siguen exportables vía FDP.
- Sin desinstalar módulos.
- Baseline alertas intacta.

## Riesgos

- UI/reportes que lean LATAM number directamente (sin FDP) en docs nuevos de emisión verán vacío hasta adaptar.
- Mitigación: FDP ya cubre exporters/PDF Justech; inventariar lecturas directas residuales en P1.

## Sincronización

- **Unidireccional emisión:** Justech → (nada) cuando dual_write OFF.
- **Expense code mirror** Justech→`l10n_do_expense_type` se mantiene (no es NCF).
- **Nunca** LATAM→Justech automático en post para recibidos.

## Rollback

Reactivar `ncf_dual_write` + restaurar módulos/backup P0.1. Ver `P0_1_ROLLBACK.md`.
