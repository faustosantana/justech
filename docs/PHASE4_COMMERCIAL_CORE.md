# Fase 4 — Núcleo Comercial (Commercial Core)

**Cliente:** Hellenia, S.R.L.  
**Ambiente:** `hellenia_dev` — https://dev.hellenia.cloud  
**Fecha:** 2026-06-30  
**Estado:** **Completado** — detenido para aprobación Fase 5 (POS exclusivamente)

---

## 1. Resumen ejecutivo

Se instaló el **núcleo comercial** en DEV: Contacts, Sales, Purchase e Inventory, con validación E2E del ciclo completo ventas/compras/inventario/facturación.

| Área | Resultado |
|------|-----------|
| Contacts (`contacts`) | ✅ Instalado |
| Sales (`sale`) | ✅ Instalado |
| Purchase (`purchase`) | ✅ Instalado |
| Inventory (`stock`) | ✅ Instalado |
| Cotizaciones → Pedidos → Entregas → Factura cliente | ✅ Validado |
| RFQ/PO → Recepciones → Factura proveedor | ✅ Validado |
| Inventario (stock almacenable) | ✅ Validado |
| Módulos prohibidos (POS, Barcode, Studio, Sign, Documents, Helpdesk, CRM) | ✅ No instalados |
| `stock_barcode` auto-dependencia | ✅ Desinstalado explícitamente |

**Backup pre-cambio:** `/opt/odoo-projects/hellenia/backups/dev/2026-06-30_0452` — verificado.

**Instalación:** `PHASE4_INSTALL ok: true` (tras desinstalar `stock_barcode`)  
**Validación:** `PHASE4_VALIDATION ok: true`

---

## 2. Módulos instalados (solicitados)

| Módulo técnico | Nombre Apps | Estado |
|----------------|-------------|--------|
| `contacts` | Contacts | installed |
| `stock` | Inventory | installed |
| `purchase` | Purchase | installed |
| `sale` | Sales | installed |

**Orden de instalación:** `contacts` → `stock` → `purchase` → `sale`

**Total módulos instalados en BD:** 108 (incluye dependencias automáticas de contabilidad EE, bridges y dashboards).

---

## 3. Módulos explícitamente NO instalados

| Módulo | Estado |
|--------|--------|
| `point_of_sale` (POS) | uninstalled |
| `stock_barcode` (Barcode) | uninstalled |
| `web_studio` (Studio) | uninstalled |
| `sign` (Sign) | uninstalled |
| `documents` (Documents) | uninstalled |
| `helpdesk` (Helpdesk) | uninstalled |
| `crm` (CRM) | uninstalled |
| `sale_crm` | uninstalled |
| `pos_sale` | uninstalled |

---

## 4. Dependencias automáticas relevantes (esperadas)

Odoo 19 EE instaló bridges estándar al activar ventas/compras/inventario sobre contabilidad ya configurada:

| Módulo | Rol |
|--------|-----|
| `sale_stock` | Pedido venta ↔ entrega |
| `purchase_stock` | PO ↔ recepción |
| `sale_purchase` | Venta ↔ compra (make-to-order) |
| `sale_purchase_stock` | Bridge completo venta-compra-stock |
| `stock_account` | Valoración inventario contable |
| `stock_enterprise` | Vistas EE inventario |
| `sale_enterprise` | Vistas EE ventas |
| `purchase_accountant` | Compras + contabilidad EE |
| `stock_accountant` | Inventario + contabilidad EE |
| `sale_account_accountant` | Ventas + contabilidad EE |

> Estas dependencias son **estándar Odoo** y no equivalen a instalar POS, CRM ni apps adicionales solicitadas fuera de alcance.

---

## 5. Incidencia resuelta: `stock_barcode`

Al instalar `stock`, Odoo 19 EE **auto-instaló** `stock_barcode` como dependencia transitiva.

**Acción aplicada:** desinstalación inmediata vía script (`install-phase4-commercial-core.py` incluye paso post-instalación).

**Estado final:** `stock_barcode` = `uninstalled`. Inventario operativo sin app Barcode.

---

## 6. Validación E2E automatizada

Script: `scripts/validate-phase4-commercial-core.py`

### 6.1 Flujo ventas

| Paso | Check | Estado | Detalle |
|------|-------|--------|---------|
| Cotización | `quotation_created` | ✅ | `draft` |
| Confirmar pedido | `sale_order_confirmed` | ✅ | `sale` |
| Crear entrega | `delivery_created` | ✅ | 1 picking salida |
| Validar entrega | `delivery_done` | ✅ | `done` |
| Factura cliente | `customer_invoice_created` | ✅ | creada |
| Publicar factura | `customer_invoice_posted` | ✅ | `posted` |

### 6.2 Flujo compras

| Paso | Check | Estado | Detalle |
|------|-------|--------|---------|
| RFQ/PO borrador | `purchase_draft` | ✅ | `draft` |
| Confirmar PO | `purchase_confirmed` | ✅ | `purchase` |
| Crear recepción | `receipt_created` | ✅ | 1 picking entrada |
| Validar recepción | `receipt_done` | ✅ | `done` |
| Factura proveedor | `vendor_bill_created` | ✅ | creada |
| Publicar factura | `vendor_bill_posted` | ✅ | `posted` |

### 6.3 Inventario

| Check | Estado | Detalle |
|-------|--------|---------|
| `inventory_tracked` | ✅ | Cantidad disponible = **6.0** unidades tras flujos |

### 6.4 Datos de prueba creados (DEV)

| Recurso | Referencia |
|---------|------------|
| Producto | `PHASE4-TEST-001` — Espejo prueba, categoría Espejos |
| Cliente | `PHASE4-CUST` |
| Proveedor | `PHASE4-VEND` |
| Almacén | `Hellenia, S.R.L.` — código `WH` |

**Nota Odoo 19:** productos con stock requieren `type: consu` (Goods) + `is_storable: True` (el valor legacy `product` ya no es válido).

---

## 7. Evidencia JSON

### Instalación

```json
{
  "phase": 4,
  "allowed": {
    "contacts": "installed",
    "stock": "installed",
    "purchase": "installed",
    "sale": "installed"
  },
  "forbidden": {
    "point_of_sale": "uninstalled",
    "stock_barcode": "uninstalled",
    "web_studio": "uninstalled",
    "sign": "uninstalled",
    "documents": "uninstalled",
    "helpdesk": "uninstalled",
    "crm": "uninstalled"
  },
  "ok": true
}
```

### Validación

```json
{
  "ok": true,
  "flows": {
    "quotation_state": "draft",
    "sale_order_state": "sale",
    "delivery_state": "done",
    "invoice_state": "draft",
    "purchase_rfq_state": "draft",
    "purchase_order_state": "purchase",
    "receipt_state": "done",
    "vendor_bill_state": "draft",
    "inventory_qty": 6.0
  }
}
```

---

## 8. Pendientes (fuera de Fase 4)

| Ítem | Fase |
|------|------|
| POS (`point_of_sale`) | **Fase 5** — próxima, exclusivamente POS |
| CRM | Fase futura — no aprobada |
| Catálogo productos real / import CSV | Post-configuración operativa |
| NCF / tipos documento fiscal | Limitación conocida on-premise 19.0 — ver G-01 |
| Logo empresa | Pendiente upload |

---

## 9. Comandos de reproducción

```bash
# Backup
/opt/odoo-projects/hellenia/scripts/backup-dev.sh
/opt/odoo-projects/hellenia/scripts/verify-backup-dev.sh /opt/odoo-projects/hellenia/backups/dev/YYYY-MM-DD_HHMM

# Instalar núcleo comercial (odoo shell)
docker compose -f /opt/odoo-projects/hellenia/docker/dev/docker-compose.yml \
  --env-file /opt/odoo-projects/hellenia/config/dev/.env \
  run --rm odoo odoo shell -d hellenia_dev --no-http \
  < scripts/install-phase4-commercial-core.py

# Validar flujos E2E
docker compose -f /opt/odoo-projects/hellenia/docker/dev/docker-compose.yml \
  --env-file /opt/odoo-projects/hellenia/config/dev/.env \
  run --rm odoo odoo shell -d hellenia_dev --no-http \
  < scripts/validate-phase4-commercial-core.py
```

---

## 10. Gate siguiente fase

| Fase | Alcance | Estado |
|------|---------|--------|
| **4 — Commercial Core** | Contacts, Sales, Purchase, Inventory | ✅ **Completada** |
| **5 — POS** | Solo `point_of_sale` y dependencias POS | ⏳ **Esperando aprobación** |

**Detenido.** No se instaló POS ni módulos adicionales.

---

**Scripts:** `install-phase4-commercial-core.py` · `validate-phase4-commercial-core.py`  
**Fase anterior:** [PHASE35_GOLDEN_CONFIGURATION_REPORT.md](PHASE35_GOLDEN_CONFIGURATION_REPORT.md)
