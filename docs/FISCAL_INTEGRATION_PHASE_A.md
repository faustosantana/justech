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
| **DEV-2** | Instalar `justech_l10n_do_reports` en erp.justech.do | justech_dev | Pendiente aprobación DEV-1 |
| **A-003** | Matriz funcional smoke (ventas/compras/NC/ND/pagos read-only) | ncf_lab | Pendiente |
| **A-004** | Multiempresa 4 compañías — validación datos reales lab | ncf_lab | Pendiente |
| **A-005** | Clon `justech_dev` → `justech_fiscal_int` + install Justech sin Adel write | nueva BD | Pendiente aprobación |
| **A-006** | Backfill metadatos histórico (solo columnas Justech, sin `_post`) | fiscal_int | Pendiente |
| **A-007** | Cutover piloto 1 empresa en fiscal_int | fiscal_int | Pendiente |

> **Nota:** Tocar `justech_dev` operativo solo tras aprobación explícita por iteración.

## Alcance Fase A (checklist)

- [ ] Facturas venta/compra
- [ ] Cotizaciones / ventas
- [ ] Contactos fiscales
- [ ] NCF asignación / void
- [ ] Secuencias y rangos
- [ ] NC / ND
- [ ] Pagos (integridad read-only)
- [ ] Conciliaciones (integridad read-only)
- [ ] Reportes 606/607/608
- [ ] Multiempresa

## Rollback por iteración

Restaurar backup BD lab + checkout commit anterior en rama `feature/fiscal-integration-phase-a`.
