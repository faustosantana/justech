# MC-1 — Arquitectura multimoneda recomendada (Justech / RD)

**Fase:** MC-1 — Auditoría (sin implementación)  
**Alcance:** Estándar corporativo para clientes República Dominicana  
**Base:** Odoo 19 Enterprise + módulos Justech/Hellenia

---

## Decisión arquitectónica

### Enfoque recomendado: **C + B (híbrido estándar Odoo)**

| Opción evaluada | Veredicto |
|-----------------|-----------|
| **A) Producto en USD** | ❌ No viable — Odoo almacena `list_price` siempre en moneda de la compañía |
| **B) Producto en DOP** | ✅ Obligatorio — moneda funcional = DOP |
| **C) Lista de precios USD** | ✅ Recomendado — precio comercial en USD vía `product.pricelist` |
| **D) Otro enfoque** | Solo como complemento: diarios bancarios por moneda (ya implementado) |

### Estándar Justech para RD

```
┌─────────────────────────────────────────────────────────────┐
│  CAPA 1 — Moneda funcional (legal/contable/fiscal)          │
│  res.company.currency_id = DOP                              │
│  Catálogo, COA, DGII, NCF, reportes financieros en DOP      │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│  CAPA 2 — Precio comercial (ventas/compras)                 │
│  product.template.list_price → DOP (referencia interna)     │
│  product.pricelist (USD/EUR) → precio de venta comercial    │
│  sale.order.currency_id ← pricelist.currency_id             │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│  CAPA 3 — Tasas de cambio                                   │
│  res.currency.rate (manual + opcional currency_rate_live)    │
│  Fuente recomendada: Banco Central RD (referencia)          │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│  CAPA 4 — Tesorería                                         │
│  BNKD (DOP) + BNKU (USD) — diarios bancarios por moneda     │
│  Pagos en moneda del documento; FX al conciliar             │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│  CAPA 5 — Diferencial cambiario                             │
│  Motor estándar Odoo → diario CAMBI                         │
│  Cuentas: 410500 (ganancia) / pérdida (revisar mapping)     │
└─────────────────────────────────────────────────────────────┘
```

---

## Por qué NO cambiar moneda del producto

En Odoo 19:

- `product.template.list_price` y `standard_price` están **siempre** denominados en `company.currency_id`.
- La pestaña "Precios" del producto muestra reglas por lista de precios; si la lista es USD, los precios mostrados/guardados en esa lista están en USD, pero el campo `list_price` general sigue en DOP.
- Esto explica la observación del usuario: **no es un bug**, es el diseño estándar de Odoo.

---

## Configuración objetivo por cliente Justech RD

| Elemento | Valor estándar |
|----------|----------------|
| Moneda compañía | DOP |
| Monedas activas | DOP, USD (+ EUR si import/export) |
| Lista pública default | DOP — clientes locales |
| Lista exportación / USD | USD — clientes internacionales, showrooms USD |
| Partner property | `property_product_pricelist` por segmento |
| Diarios banco | BNKD (DOP), BNKU (USD) |
| Diario FX | CAMBI |
| Tasas | Manual diaria/semanal; integración BCRD como mejora |
| POS | DOP únicamente (v1); multimoneda POS = roadmap |

---

## Separación de responsabilidades

| Capa | Módulo Odoo | Custom Justech |
|------|-------------|----------------|
| Moneda documento | `account`, `sale`, `purchase` | UI labels (`hellenia_ux`) |
| Tasas | `res.currency.rate` | Ninguno |
| Precios comerciales | `product.pricelist` | Script Fase 8 (solo DOP) |
| Pagos multimoneda | `account.payment` | `hellenia_account` (BNKD/BNKU) |
| FX automático | `account` reconcile | Ninguno |
| DGII 606/607 | — | Montos en DOP (`*_signed`) |
| DGII 609 | — | Moneda + tasa explícita |
| PDF | QWeb estándar | `justech_report_design` |

---

## Anti-patrones a evitar

1. Cambiar `company.currency_id` a USD en clientes RD.
2. Duplicar productos (SKU-DOP / SKU-USD) solo por moneda.
3. Hardcodear tasas en `price_unit` sin congelar `invoice_currency_rate`.
4. Pagar factura USD desde wizard sin seleccionar moneda USD.
5. Mapear pérdida cambiaria a cuenta de gastos bancarios genéricos sin revisión contable.

---

## Certificación MC-1 (criterios Go Live)

| # | Criterio | Estado actual Hellenia |
|---|----------|------------------------|
| 1 | DOP moneda funcional | ✅ Configurado |
| 2 | USD activo con tasas | ⚠️ Manual; verificar periodicidad |
| 3 | Lista USD formal | ❌ Pendiente (solo DOP en Fase 8) |
| 4 | BNKD/BNKU operativos | ✅ Implementado |
| 5 | CAMBI + cuentas FX | ⚠️ CAMBI OK; cuenta pérdida cuestionable |
| 6 | UAT USD E2E (SO→INV→PAY→FX) | ❌ No certificado |
| 7 | DGII 607 con facturas USD | ⚠️ Funciona en DOP equivalente; validar con contador |
| 8 | PDF muestra moneda | ✅ Parcial (sin tasa ni equivalente DOP) |

---

## Referencias código

- `config/company/company.yaml` — DOP
- `custom/hellenia_account/models/payment_bank_setup.py` — BNKD/BNKU
- `scripts/apply-phase8-parameterization.py` — Lista pública DOP
- `docs/COMMERCIAL_CONFIGURATION.md` — Lista USD pendiente
- `docs/ERP_FINANCIAL_ARCHITECTURE.md` §14 — FX estándar Odoo
