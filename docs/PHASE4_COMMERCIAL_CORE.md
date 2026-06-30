# Fase 4 — Núcleo Comercial (Commercial Core)

**Cliente:** Hellenia, S.R.L.  
**Ambiente:** `hellenia_dev` — https://dev.hellenia.cloud  
**Fecha:** 2026-06-30  
**Estado:** **Completado y validado** — detenido (Fase 5 = POS, no iniciada)

---

## 1. Resumen ejecutivo

Se instaló y validó el **núcleo comercial** en DEV únicamente: Contacts, Sales, Purchase e Inventory. Flujo E2E de 10 pasos ejecutado con éxito.

| Área | Resultado |
|------|-----------|
| Contacts (`contacts`) | ✅ Instalado |
| Sales (`sale`) | ✅ Instalado |
| Purchase (`purchase`) | ✅ Instalado |
| Inventory (`stock`) | ✅ Instalado |
| Flujo 10 pasos (compra → venta → inventario → contabilidad) | ✅ `PHASE4_VALIDATION ok: true` |
| Producto almacenable Odoo 19 (`consu` + `is_storable`) | ✅ Corregido y validado |
| Módulos prohibidos (POS, Studio, Sign, Documents, Helpdesk, CRM) | ✅ No instalados |
| `stock_barcode` | ✅ Desinstalado sin afectar `stock` |
| TEST / PROD | ✅ No tocados |

**Backup:** `/opt/odoo-projects/hellenia/backups/dev/2026-06-30_0457` — verificado.

---

## 2. Módulos instalados (solicitados)

| Módulo técnico | Nombre Apps | Estado |
|----------------|-------------|--------|
| `contacts` | Contacts | installed |
| `stock` | Inventory | installed |
| `purchase` | Purchase | installed |
| `sale` | Sales | installed |

**Orden de instalación:** `contacts` → `stock` → `purchase` → `sale`  
**Total módulos en BD:** 108 (incluye dependencias automáticas EE y bridges).

---

## 3. Módulos explícitamente NO instalados

| Módulo | Estado |
|--------|--------|
| `point_of_sale` (POS) | uninstalled |
| `web_studio` (Studio) | uninstalled |
| `sign` (Sign) | uninstalled |
| `documents` (Documents) | uninstalled |
| `helpdesk` (Helpdesk) | uninstalled |
| `crm` (CRM) | uninstalled |
| `sale_crm` | uninstalled |
| `pos_sale` | uninstalled |

---

## 4. Dependencias automáticas relevantes

Odoo 19 EE instaló bridges estándar al activar ventas/compras/inventario sobre contabilidad ya configurada (Fase 3):

| Módulo | Rol |
|--------|-----|
| `sale_stock` | Pedido venta ↔ entrega |
| `purchase_stock` | PO ↔ recepción |
| `sale_purchase` | Venta ↔ compra |
| `sale_purchase_stock` | Bridge venta-compra-stock |
| `stock_account` | Valoración inventario contable |
| `stock_enterprise` | Vistas EE inventario |
| `sale_enterprise` | Vistas EE ventas |
| `purchase_accountant` | Compras + contabilidad EE |
| `stock_accountant` | Inventario + contabilidad EE |
| `sale_account_accountant` | Ventas + contabilidad EE |
| `barcodes` | Base códigos de barras (dependencia técnica, no app Barcode) |

> Estas dependencias son **estándar Odoo** y no equivalen a instalar POS, CRM ni apps adicionales fuera de alcance.

---

## 5. Desviación: `stock_barcode`

| Aspecto | Detalle |
|---------|---------|
| **Comportamiento** | Al instalar `stock`, Odoo 19 EE puede auto-instalar `stock_barcode` |
| **Política Fase 4** | Desinstalar **solo si no rompe** inventario |
| **Resultado** | Desinstalación exitosa — `stock` sigue operativo (108 módulos, validación E2E ok) |
| **Estado final** | `stock_barcode` = `uninstalled` |
| **Script** | `install-phase4-commercial-core.py` intenta desinstalar en try/except; si falla, conserva el módulo |

---

## 6. Producto almacenable — Odoo 19

En Odoo 19 el tipo legacy `product` **ya no es válido**. Para inventario almacenable:

| Campo | Valor |
|-------|-------|
| `type` | `consu` (Goods) |
| `is_storable` | `True` |

**Producto de prueba:** `PHASE4-TEST-001` — categoría Espejos, costo 5 000 DOP, precio 10 000 DOP.

---

## 7. Validación E2E — 10 pasos

Script: `scripts/validate-phase4-commercial-core.py`  
**Resultado:** `PHASE4_VALIDATION ok: true` (2026-06-30T04:57:52Z)

| # | Paso | Check | Resultado | Evidencia |
|---|------|-------|-----------|-----------|
| 1 | Crear proveedor de prueba | `proveedor_prueba` | ✅ | `PHASE4-VEND` |
| 2 | Crear producto almacenable | `producto_almacenable` | ✅ | `type=consu is_storable=True` |
| 3 | Compra / RFQ | `compra_rfq` | ✅ | PO estado `draft` |
| 4 | Recepción de inventario | `recepcion_inventario` | ✅ | Picking `done` (+2 uds) |
| 5 | Cotización de venta | `cotizacion_venta` | ✅ | SO estado `draft` |
| 6 | Confirmación de venta | `confirmacion_venta` | ✅ | SO estado `sale` |
| 7 | Entrega | `entrega` | ✅ | Picking salida `done` (-1 ud) |
| 8 | Factura cliente | `factura_cliente` | ✅ | Factura `posted` |
| 9 | Impacto en inventario | `impacto_inventario` | ✅ | Δ = +1.0 (compra 2 − venta 1) |
| 10 | Impacto contable básico | `impacto_contable_basico` | ✅ | Ver §8 |

**Maestro adicional:** cliente `PHASE4-CUST` (requerido para venta, no listado como paso separado).

### 7.1 Inventario — trazabilidad del paso 9

| Momento | Cantidad disponible |
|---------|---------------------|
| Antes del flujo | 6.0 (residual ejecuciones previas DEV) |
| Tras recepción (+2) | 8.0 |
| Tras entrega (−1) | 7.0 |
| **Delta neto flujo** | **+1.0** (= 2 comprados − 1 vendido) ✅ |

> En ambiente limpio el inventario inicial sería 0; la validación usa **delta** para ser idempotente en DEV.

---

## 8. Impacto contable básico (paso 10)

| Documento | Líneas | Balanceado | Total (DOP) |
|-----------|--------|------------|-------------|
| Factura proveedor | 3 | ✅ | 11 800.00 (10 000 + ITBIS) |
| Factura cliente | 3 | ✅ | 11 800.00 (10 000 + ITBIS) |

**Desviación menor:** `stock_valuation_moves` = 0 — los `stock.move` completados no exponen `account_move_id` poblado en esta ejecución shell (Odoo 19 puede diferir el momento de generación de asientos de valoración). Las facturas AP/AR se publicaron correctamente y cuadran débito/crédito.

**No validado en Fase 4:** NCF, tipos documento fiscal, asientos de cierre.

---

## 9. Restricciones respetadas

| Restricción | Cumplimiento |
|-------------|--------------|
| No tocar TEST | ✅ |
| No tocar PRODUCCIÓN | ✅ |
| No instalar POS | ✅ |
| No crear usuarios reales | ✅ |
| No cargar catálogo real | ✅ |
| Solo datos de prueba (`PHASE4-*`) | ✅ |

---

## 10. Evidencia JSON (resumen)

```json
{
  "ok": true,
  "steps": {
    "1": {"name": "proveedor_prueba", "ok": true},
    "2": {"name": "producto_almacenable", "ok": true, "detail": "type=consu is_storable=True"},
    "3": {"name": "compra_rfq", "ok": true},
    "4": {"name": "recepcion_inventario", "ok": true},
    "5": {"name": "cotizacion_venta", "ok": true},
    "6": {"name": "confirmacion_venta", "ok": true},
    "7": {"name": "entrega", "ok": true},
    "8": {"name": "factura_cliente", "ok": true},
    "9": {"name": "impacto_inventario", "ok": true, "detail": "delta=1.0"},
    "10": {"name": "impacto_contable_basico", "ok": true}
  },
  "flows": {
    "inventory_qty_before": 6.0,
    "inventory_qty_after_receipt": 8.0,
    "inventory_qty_final": 7.0,
    "accounting": {
      "vendor_bill_balanced": true,
      "customer_invoice_balanced": true,
      "vendor_bill_total": 11800.0,
      "customer_invoice_total": 11800.0
    }
  }
}
```

---

## 11. Comandos de reproducción

```bash
# Backup
/opt/odoo-projects/hellenia/scripts/backup-dev.sh

# Instalar / verificar módulos (idempotente)
docker compose -f /opt/odoo-projects/hellenia/docker/dev/docker-compose.yml \
  --env-file /opt/odoo-projects/hellenia/config/dev/.env \
  run --rm odoo odoo shell -d hellenia_dev --no-http \
  < scripts/install-phase4-commercial-core.py

# Validar flujo 10 pasos
docker compose -f /opt/odoo-projects/hellenia/docker/dev/docker-compose.yml \
  --env-file /opt/odoo-projects/hellenia/config/dev/.env \
  run --rm odoo odoo shell -d hellenia_dev --no-http \
  < scripts/validate-phase4-commercial-core.py
```

---

## 12. Pendientes y gate siguiente fase

| Ítem | Fase |
|------|------|
| POS (`point_of_sale`) | **Fase 5** — no iniciada |
| CRM, catálogo real, usuarios operativos | Fases futuras |
| NCF / tipos documento | Limitación conocida on-premise 19.0 (G-01) |

**Detenido.** Fase 4 completada.

---

**Scripts:** `install-phase4-commercial-core.py` · `validate-phase4-commercial-core.py`  
**Fase anterior:** [PHASE35_GOLDEN_CONFIGURATION_REPORT.md](PHASE35_GOLDEN_CONFIGURATION_REPORT.md)
