# Informe de Preparación UAT — Hellenia

**Fase:** 8 — Cierre parametrización funcional  
**Fecha:** 2026-06-30  
**Ambiente parametrizado:** DEV (`hellenia_dev`)  
**UAT planificado en:** TEST (tras aprobación y promoción)  
**Estado:** **LISTO PARA APROBACIÓN** — UAT **NO INICIADO**

---

## 1. Resumen ejecutivo

El ERP en DEV está parametrizado funcionalmente para representar la operación de Hellenia. El sistema está **listo para ser probado por el cliente** una vez aprobada esta fase y promovida la configuración a TEST.

| Dimensión | Preparación UAT |
|-----------|-----------------|
| Configuración general | 90% — pendiente SMTP, pie documentos |
| Comercial | 85% — pendiente políticas negocio |
| Compras | 85% — pendiente aprobaciones |
| Inventario | 90% — pendiente política lotes |
| Productos | Estructura lista — catálogo pendiente Hellenia |
| Contabilidad | 95% — pendiente firma contador |
| Localización RD | 95% — pendiente rangos DGII reales |
| Reportes | 90% — pendiente validación formato DGII |
| Sistema | 80% — pendiente SMTP |
| Datos piloto | ✅ Mínimos creados |

---

## 2. Datos piloto UAT (DEV)

Registros mínimos creados Fase 8 — **no son datos reales**:

| Tipo | Ref | Nombre |
|------|-----|--------|
| Cliente | UAT-PILOT-CUST-001 | Cliente Piloto UAT |
| Proveedor | UAT-PILOT-VEND-001 | Proveedor Piloto UAT |
| Producto | UAT-PILOT-PROD-001 | Producto Piloto UAT — Espejo muestra |

Registros heredados Fase 4 (prueba E2E):

| Ref | Tipo |
|-----|------|
| PHASE4-CUST | Cliente |
| PHASE4-VEND | Proveedor |
| PHASE4-TEST-001 | Producto |

**Recomendación UAT:** usar prefijo `UAT-PILOT-*` o limpiar `PHASE4-*`.

---

## 3. Escenarios UAT sugeridos (no ejecutados)

| # | Escenario | Módulos | Datos |
|---|-----------|---------|-------|
| 1 | Cotización → pedido → entrega → factura B01/B02 | Ventas + Inventario + Fiscal | Piloto |
| 2 | Compra → recepción → factura proveedor B11 | Compras + Inventario | Piloto |
| 3 | Nota de crédito B04 | Ventas + Fiscal | Piloto |
| 4 | Pago cliente (efectivo/transferencia) | Contabilidad | Piloto |
| 5 | Reporte 607 / 606 / 608 | Fiscal | Movimientos piloto |
| 6 | Inventario físico / ajuste | Inventario | Piloto |
| 7 | PDF factura con NCF | Fiscal | Verificar logo/pie |

---

## 4. Checklist pre-UAT

| # | Item | Estado | Responsable |
|---|------|--------|-------------|
| 1 | Aprobación Fase 8 | ⏳ | Hellenia |
| 2 | Backup TEST | ⏳ | Justech |
| 3 | Promoción DEV → TEST | ⏳ | Justech |
| 4 | Crear usuarios ROLE_MATRIX | ⏳ | Justech |
| 5 | SMTP configurado | ⏳ | Justech + Hellenia |
| 6 | Rangos NCF DGII | ⏳ | Hellenia |
| 7 | Catálogo piloto ampliado | ⏳ | Hellenia |
| 8 | Políticas comerciales documentadas | ⏳ | Hellenia |
| 9 | Firma contador plan cuentas | ⏳ | Glys Nuñez |
| 10 | Plan escenarios UAT firmado | ⏳ | Hellenia + Justech |

---

## 5. Certificación UAT Readiness

### Estado por bloque

| Bloque | Validación Fase 8 |
|--------|-------------------|
| Configuración general | PASS CON OBSERVACIONES |
| Comercial | PASS CON OBSERVACIONES |
| Compras | PASS CON OBSERVACIONES |
| Inventario | PASS CON OBSERVACIONES |
| Productos | PASS CON OBSERVACIONES |
| Contabilidad | PASS CON OBSERVACIONES |
| Localización dominicana | **PASS** |
| Reportes | PASS CON OBSERVACIONES |
| Sistema | PASS CON OBSERVACIONES |
| Datos piloto | PASS CON OBSERVACIONES |

**Global:** **PASS CON OBSERVACIONES**

### Pendientes antes del UAT

1. Aprobación explícita de esta certificación  
2. Usuarios funcionales (8 roles diseñados — 0 creados)  
3. SMTP corporativo  
4. Rangos NCF autorizados DGII  
5. Catálogo productos (mínimo ampliado)  
6. Políticas descuento/devolución/garantía  
7. Promoción configuración a TEST  

### Pendientes antes del Go-Live

Ver [GO_LIVE_READINESS.md](GO_LIVE_READINESS.md) — infraestructura producción completa.

### Riesgos UAT

| ID | Riesgo | Mitigación |
|----|--------|------------|
| UAT-R01 | Sin SMTP | Configurar antes o excluir escenarios correo |
| UAT-R02 | Rangos NCF prueba | Usar solo en TEST; no documentos reales |
| UAT-R03 | Sin usuarios negocio | Crear al aprobar según matriz |
| UAT-R04 | Datos PHASE4 mezclados | Limpiar o etiquetar en TEST |

### Recomendaciones

1. Ejecutar UAT en **TEST** neutralizado inicialmente; habilitar SMTP solo para pruebas correo.  
2. Asignar escenarios por rol según [ROLE_MATRIX.md](ROLE_MATRIX.md).  
3. Incluir contador en escenarios fiscales 606/607/608.  
4. Documentar incidencias en plantilla UAT (crear en fase siguiente).  
5. No usar DEV para UAT formal — promover a TEST tras aprobación.

---

## 6. Evidencia

| Archivo | Descripción |
|---------|-------------|
| `evidence/phase8-audit-dev.json` | Auditoría 10 bloques |
| `evidence/phase8-apply-dev.json` | 15 acciones parametrización |
| `backups/dev/2026-06-30_1400` | Backup pre-Fase 8 |

### Validaciones técnicas

| Script | Resultado |
|--------|-----------|
| `validate-phase35-golden-config.sh dev` | ✅ ok: true |
| `validate-phase6-mvp.sh dev` | ✅ ok: true |

---

## 7. Declaración final

```
╔══════════════════════════════════════════════════════════════╗
║  FASE 8 — CERTIFICACIÓN PARAMETRIZACIÓN FUNCIONAL          ║
╠══════════════════════════════════════════════════════════════╣
║  Ambiente:              DEV (hellenia_dev)                  ║
║  Parametrización:        COMPLETA (con observaciones)       ║
║  MVP fiscal:             VALIDADO                           ║
║  Datos piloto:           CREADOS                            ║
║  Catálogo real:          NO CARGADO (por diseño)          ║
║  Usuarios funcionales:   NO CREADOS (por diseño)          ║
║  TEST / PRODUCCIÓN:      NO MODIFICADOS                     ║
║  UAT funcional:          NO INICIADO — ESPERANDO APROBACIÓN ║
╚══════════════════════════════════════════════════════════════╝

Fecha:     2026-06-30
Backup:    backups/dev/2026-06-30_1400
Rama:      feature/justech-l10n-do-mvp
```

---

## 8. Referencias

- [PHASE8_FUNCTIONAL_PARAMETERIZATION.md](PHASE8_FUNCTIONAL_PARAMETERIZATION.md)
- [PHASE75_CERTIFICATION.md](PHASE75_CERTIFICATION.md)
- [UAT_ENVIRONMENT_PREPARATION.md](UAT_ENVIRONMENT_PREPARATION.md)
- [ROLE_MATRIX.md](ROLE_MATRIX.md)

---

**Detenido.** Esperando aprobación para iniciar UAT funcional.
