# Retenciones dominicanas — Configuración y uso

**Fuente:** `l10n_do` (Odoo estándar RD) — **no se inventan tasas**  
**Módulo Hellenia:** `hellenia_account` solo **activa** impuestos clave  
**Validación:** `scripts/phase16-validate-payments-test.py`

---

## 1. Principio

Las retenciones ISR/ITBIS provienen del plan fiscal dominicano cargado por `l10n_do`. Hellenia **no crea impuestos custom**; documenta y activa los existentes.

Aplicación típica: en **líneas de factura** (venta/compra) vía impuestos o posición fiscal — no como módulo de retención separado.

---

## 2. Retenciones prioritarias Fase 16

### 2.1 5% ISR Gobierno (ventas)

| Campo | Valor |
|-------|-------|
| **Impuesto Odoo** | `-5% ISR Gov.` |
| **Tasa** | -5% |
| **Tipo** | `sale` (retención en factura a entidad gubernamental) |
| **Base** | Monto gravable de la factura |
| **Posición fiscal** | `Governmental` |
| **Cuenta contable** | Asignada por `l10n_do` en definición del impuesto |
| **Cuándo aplica** | Ventas a organismos del Estado que retienen ISR |
| **606** | No aplica (es venta) |
| **607** | La factura aparece en ventas; retención en líneas de impuesto |

### 2.2 30% ITBIS retenido (compras — servicios legales N02-05)

| Campo | Valor |
|-------|-------|
| **Impuesto Odoo** | `-30% ITBIS Leg. (N02-05)` |
| **Tasa efectiva** | -5.4% del monto (30% del ITBIS 18%) |
| **Tipo** | `purchase` |
| **Base** | ITBIS de la línea (impuesto hijo en grupo) |
| **Posición fiscal** | `P. Legal Services` |
| **Cuándo aplica** | Pagos a proveedores de servicios legales sujetos a retención ITBIS |
| **606** | Columnas ITBIS retenido en compras |
| **607** | No aplica |

**Variante profesional:** `-30% ITBIS Prof. (N02-05)` — misma lógica para servicios profesionales.

### 2.3 10% proveedor informal (ISR Fee)

| Campo | Valor |
|-------|-------|
| **Impuesto Odoo** | `-10% ISR Fee` |
| **Tasa** | -10% |
| **Tipo** | `purchase` |
| **Base** | Monto del servicio/bien |
| **Posición fiscal** | `Informal Supplier of Goods` |
| **Documento** | Comprobante **B11** (proveedor informal) |
| **Cuándo aplica** | Compras a proveedores informales según normativa |
| **606** | Compras con retención ISR |
| **607** | No aplica |

### 2.4 75% ITBIS — proveedor informal bienes (N08-10)

| Campo | Valor |
|-------|-------|
| **Impuesto Odoo** | `-75% ITBIS (N08-10)` |
| **Tasa efectiva** | -13.5% (75% del ITBIS 18%) |
| **Tipo** | `purchase` |
| **Posición fiscal** | `Informal Supplier of Goods` |
| **Cuándo aplica** | Retención ITBIS en compras a informales |
| **606** | ITBIS retenido compras |

> **Nota:** El requisito "10% proveedor informal" en operaciones Hellenia se cubre con **`-10% ISR Fee`** (ISR). La retención ITBIS informal es **75% del ITBIS** (`-75% ITBIS (N08-10)`), no 10% del monto — documentado según `l10n_do`.

---

## 3. Otras retenciones disponibles en `l10n_do`

Verificadas en certificación fiscal (`docs/DOMINICAN_FISCAL_CERTIFICATION.md`):

| Impuesto | Tasa | Uso |
|----------|------|-----|
| `-100% ITBIS (N07-09)` | -18% | purchase |
| `-100% ITBIS (N01-11)` | -18% | purchase |
| `-27% ISR (L253-12)` | -27% | purchase |
| `-10% ISR Rent.` | -10% | purchase |
| `-2% ISR (N07-07)` | -2% | purchase |
| `-2% ISR Mat.` | -2% | purchase |
| … | … | Total ~12 retenciones activas |

**Total impuestos plan `do`:** 37 (14 variantes ITBIS).

---

## 4. Posiciones fiscales relacionadas

| Posición | Retenciones típicas |
|----------|---------------------|
| DO Domestic | ITBIS estándar |
| Governmental | -5% ISR Gov. (venta) |
| Informal Supplier of Goods | -10% ISR Fee, -75% ITBIS |
| P. Legal Services | -30% ITBIS Leg. |
| P. Physical Services | Retenciones servicios físicos |
| Outside Services | Servicios exterior |
| Non-Profit Services | Exenciones / tasas especiales |

---

## 5. Configuración en Hellenia

```python
# hellenia_account — configure_withholding_reference()
# Activa si estaban inactivos:
-5% ISR Gov.          (sale)
-30% ITBIS Leg.       (purchase)
-10% ISR Fee          (purchase)
-75% ITBIS (N08-10)   (purchase)
-30% ITBIS Prof.      (purchase, si existe)
```

---

## 6. Retenciones pendientes / fuera de alcance MVP

| Item | Estado | Notas |
|------|--------|-------|
| Wizard retención en **pago** (no en factura) | No implementado | Odoo RD estándar usa impuestos en factura |
| Retenciones en **pagos a extranjeros** (609) | Fuera MVP | Roadmap DGII |
| Validación contador sobre cada cuenta retención | Pendiente | UAT con Glys Nuñez |
| UI selección retención en wizard pago múltiple | No requerido Fase 16 | Aplicar impuesto en factura |

---

## 7. Impacto reportes DGII

| Retención | 606 (compras) | 607 (ventas) |
|-----------|---------------|--------------|
| -5% ISR Gov. | — | Monto facturado + impuestos |
| -30% ITBIS Leg. | ITBIS retenido | — |
| -10% ISR Fee | Retención ISR | — |
| -75% ITBIS N08-10 | ITBIS retenido informal | — |

Generación: **Contabilidad → Reportes DGII → 606 / 607** (`justech_l10n_do_reports`).

---

## 8. Referencias normativas

- Norma N02-05 — retención ITBIS servicios profesionales/legales  
- Norma N08-10 — retención ITBIS proveedores informales  
- Norma General 07-2018 — formatos 606/607  
- DGII: [Formatos envío datos](https://dgii.gov.do/cicloContribuyente/obligacionesTributarias/remisionInformacion/Paginas/formatoEnvioDatos.aspx)
