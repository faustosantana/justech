# Configuración NCF — Hellenia

**Fase:** 12  
**Estado:** Tipos documento **PASS** — Rangos DGII **FAIL** (pendiente cliente)

---

## 1. Tipos documento activos (Justech producto)

| Prefijo | Nombre | Estado |
|---------|--------|--------|
| B01 | Factura de Crédito Fiscal | ✅ |
| B02 | Factura de Consumo | ✅ |
| B03 | Nota de Débito | ✅ |
| B04 | Nota de Crédito | ✅ |
| B11 | Comprobante de Compras | ✅ |
| B13 | Gastos Menores | ✅ |

Configurados en `justech_l10n_do_base` — **no modificar en Fase 12**.

---

## 2. Rangos NCF

### Estado actual

| Ambiente | Rangos UAT/prueba | Rangos DGII reales |
|----------|-------------------|-------------------|
| TEST | Eliminados parcialmente / histórico en backup | **0** |
| DEV | Rangos laboratorio posibles | **0** |
| PROD | N/A | **0** — BD no creada |

### Fase 12 — acciones realizadas

- Eliminación rangos UAT sin facturas publicadas
- Documentación plantilla: `data/hellenia/templates/ncf_rangos_dgii_template.csv`
- **No** se inventaron números de autorización DGII

---

## 3. Entregable requerido (Cliente / Contador)

Por cada tipo B01, B02, B03, B04, B11, B13:

| Campo | Descripción |
|-------|-------------|
| Número autorización DGII | De la autorización impresa |
| Secuencia inicial / final | Del rango autorizado |
| Fecha vigencia | Desde / hasta |
| Diario Odoo | INV (ventas) o FACTU (compras) |

---

## 4. Procedimiento carga Go-Live (Justech)

1. Recibir autorizaciones DGII verificadas por contador
2. En `hellenia_prod`: Contabilidad → Fiscal Dominicano → Rangos NCF
3. Crear un rango por tipo/prefijo según autorización
4. Activar solo rangos vigentes
5. Verificar `next_sequence` = secuencia inicial DGII
6. Prueba: 1 factura borrador → NCF asignado → **no publicar** hasta validación
7. Eliminar cualquier rango UAT residual

```bash
# Validación post-carga
./scripts/validate-phase6-mvp.sh  # en prod tras despliegue
```

---

## 5. Diarios con NCF

| Diario | NCF |
|--------|-----|
| INV (ventas) | B01, B02, B03, B04 |
| FACTU (compras) | B11, B13 |

Verificar en: Contabilidad → Configuración → Diarios → pestaña fiscal Justech.

---

## 6. Certificación Fase 12

| Item | Estado |
|------|--------|
| Tipos B01–B13 | **PASS** |
| Rangos prueba eliminados (prod path) | **PASS** (BD nueva) |
| Rangos DGII reales | **FAIL** |
| Validación numeración real | **FAIL** |
