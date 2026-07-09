# Fase A — Integración fiscal Justech en erp.justech.do

| Metadato | Valor |
|----------|-------|
| **Entorno** | erp.justech.do (207.244.242.58) |
| **Producción** | justgroup.app — **PROHIBIDO** |
| **BD operativa** | `justech_dev` — Adel activo; histórico **intocable** |
| **BD integración** | `justech_ncf_lab` — clon aislado; validación destructiva permitida |
| **Rama** | `feature/fiscal-integration-phase-a` |
| **PDD aprobado** | Diseño Fiscal Center **congelado** hasta estabilización |

## Reglas

1. Cada iteración: código estable → tests PASS → evidencia → commit → push.
2. Sin merge hasta aprobación explícita del propietario.
3. Sin avanzar iteración N+1 hasta aprobación de N.
4. Si una mejora rompe compatibilidad: **DETENER → CORREGIR → RE-PROBAR**.
5. Prohibido: repostear, recalcular asientos, modificar pagos/conciliaciones/histórico.

## Mapa de bases de datos

| BD | Rol | Stack fiscal |
|----|-----|--------------|
| `justech_dev` | Operativo erp.justech.do | Adel `l10n_do_accounting` — 2.255 posted, ~1.504 NCF |
| `justech_ncf_lab` | Lab integración Justech | `justech_l10n_do_*` — histórico clon intacto |

## Iteraciones planificadas

| ID | Objetivo | BD | Estado |
|----|----------|-----|--------|
| **A-001** | Baseline read-only + tests NCF + integridad lab | ncf_lab + audit dev | ✅ Aprobada |
| **DEV-1** | Install base+ncf en `justech_dev` (Adel coexistencia) | justech_dev | ✅ Completada |
| **DEV-2** | Instalar `justech_l10n_do_reports` en erp.justech.do | justech_dev | ✅ Completada |
| **FDP** | Fiscal Data Provider — lectura Adel/Justech unificada | justech_dev | ✅ Completada 2026-07-09 |
| **CLASSIFIER** | Clasificador DGII parametrizable `19.0.1.16.1` | justech_dev | ✅ **Punto estable** 2026-07-09 |
| **A-003** | Matriz funcional smoke (ventas/compras/NC/ND/pagos read-only) | ncf_lab | Pendiente |
| **A-004** | Multiempresa 4 compañías — validación datos reales lab | ncf_lab | Pendiente |
| **A-005** | Clon `justech_dev` → `justech_fiscal_int` + install Justech sin Adel write | nueva BD | Pendiente aprobación |
| **A-006** | Backfill metadatos histórico (solo columnas Justech, sin `_post`) | fiscal_int | Pendiente — **gate NCF** |
| **A-007** | Cutover piloto 1 empresa en fiscal_int | fiscal_int | Pendiente — **gate NCF** |
| **NCF-ON** | Activar motor NCF Justech (`justech_do_fiscal_enabled`) | lab → dev → prod | ⛔ **Bloqueado** — ver `NCF_MOTOR_GATE_CHECKLIST.md` |

> **Nota:** Tocar `justech_dev` operativo solo tras aprobación explícita por iteración.

## Punto estable 2026-07-09 (cerrado)

| Entrega | Resultado |
|---------|-----------|
| Fiscal Data Provider | ✅ 606 NCF: 90 errores → 0 |
| Clasificador DGII | ✅ 606 impuestos: 5 errores CDT → 0; 90/90 válidos |
| Histórico | ✅ 2255 posted, 947 reconciles, 677 pagos, 1504 NCF Adel |
| Adel | ✅ Activo |
| Motor NCF Justech | ⛔ Desactivado (0 empresas fiscal_enabled) |
| Rama | `feature/fiscal-integration-phase-a` @ `91b0123` — **sin merge** |

Evidencia: `evidence/fiscal-integration/PHASE_A_EXECUTIVE_SUMMARY.md`

## Alcance Fase A (checklist)

- [x] Reportes 606/607/608/609 lectura vía FDP (dev)
- [x] Clasificación impuestos DGII parametrizable
- [x] Pagos (integridad read-only verificada)
- [x] Conciliaciones (integridad read-only verificada)
- [ ] Facturas venta/compra — emisión Justech NCF
- [ ] Cotizaciones / ventas
- [ ] Contactos fiscales
- [ ] NCF asignación / void — motor Justech
- [ ] Secuencias y rangos DGII reales
- [ ] NC / ND con motor Justech
- [ ] Multiempresa cutover

## Rollback por iteración

Restaurar backup BD lab + checkout commit anterior en rama `feature/fiscal-integration-phase-a`.
