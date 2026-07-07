# MC-1 — Informe de auditoría multimoneda (USD/DOP)

**Fase:** MC-1 — Certificación profesional (solo auditoría)  
**Fecha:** 2026-07-07  
**Instancia analizada:** Código + documentación + evidencia read-only (sin acceso live PROD/TEST)  
**Restricciones cumplidas:** Sin cambios de código, datos, tasas, listas, commit ni push

---

## Resumen ejecutivo

Hellenia opera con **DOP como moneda funcional** y **USD limitado a tesorería bancaria** (diario BNKU). El mecanismo de listas de precios en USD que observó el usuario es **comportamiento estándar de Odoo**, no una inconsistencia: `list_price` siempre está en moneda de compañía (DOP), mientras la pestaña Precios refleja reglas de listas que pueden estar en USD.

**Veredicto:** Arquitectura parcialmente correcta para RD, pero **incompleta para certificación Go Live multimoneda**. Faltan lista USD formal, UAT end-to-end FX, revisión contable de cuentas de diferencial, y mejoras PDF/fiscal documentadas.

**Recomendación:** Adoptar estándar **DOP funcional + listas USD comerciales + motor FX Odoo** (ver `ARCHITECTURE.md`).

---

## 1. Configuración de compañías

| Aspecto | Estado Hellenia/Justech | Fuente |
|---------|-------------------------|--------|
| Moneda principal | **DOP** | `config/company/company.yaml`, audits |
| Monedas secundarias | **USD** activo (EUR posible vía Odoo estándar) | `COMMERCIAL_CONFIGURATION.md` |
| Precisión decimal | Odoo default por moneda (DOP/USD: 2 decimales) | Estándar |
| Redondeo | `res.currency.rounding` + `account.cash.rounding` si aplica | Estándar |
| Política redondeo ITBIS | Por línea (Odoo estándar) | Validado Fase 4/6 |

---

## 2. Monedas

| Moneda | Rol | Estado |
|--------|-----|--------|
| DOP | Funcional, NCF, DGII, reportes | ✅ Principal |
| USD | Ventas/compras internacionales, banco ahorro | ⚠️ Parcial |
| EUR | No documentado en Hellenia | Opcional Odoo |

---

## 3. Tipos de cambio

| Pregunta | Respuesta |
|----------|-----------|
| ¿Dónde se almacenan? | Modelo `res.currency.rate` (fecha, tasa, moneda) |
| ¿Historial? | Sí — una fila por fecha; Odoo usa la tasa vigente a la fecha del documento |
| ¿Manual? | ✅ Sí — política documentada para USD |
| ¿Automático? | Odoo EE `currency_rate_live` disponible; **no integrado en custom Justech** |
| ¿API Banco Central RD? | No implementado; posible vía `currency_rate_live` custom provider o cron |
| ¿DGII? | DGII no publica tasa para operaciones comerciales generales; 609 requiere tasa en factura extranjera |

**Campo congelado en factura (Odoo 19):** `account.move.invoice_currency_rate`

---

## 4. Productos — cómo funciona realmente Odoo

| Campo | Moneda real | Notas |
|-------|-------------|-------|
| `list_price` | **Moneda compañía (DOP)** | Siempre; no configurable por producto |
| `standard_price` | **DOP** | Costo en moneda funcional |
| Pestaña Precios | **Moneda de cada pricelist** | Reglas fijas o % sobre base |
| Variantes | Heredan template; reglas por variante posibles | Estándar |
| Atributos | No afectan moneda | Estándar |

**Flujo de cálculo en cotización:**

1. SO toma `pricelist_id` → define `currency_id` del pedido.
2. Motor `_get_product_price` / reglas pricelist calcula `price_unit` en moneda del pedido.
3. Si pricelist USD y `list_price` DOP, Odoo convierte usando tasa del día del pedido.

**Custom Justech:** Ningún override de `list_price` ni pricelist en módulos productivos.

---

## 5. Listas de precios

| Aspecto | Hellenia actual | Estándar Odoo |
|---------|-----------------|---------------|
| Listas múltiples | Default DOP + "Lista pública DOP" | ✅ |
| Lista USD | **Pendiente** (doc Fase 8) | Requerida para certificación |
| Moneda por lista | `product.pricelist.currency_id` | Una moneda por lista |
| Prioridades | Secuencia de reglas dentro de lista | Estándar |
| Por cliente | `property_product_pricelist` en partner | Estándar |
| Por categoría/producto | Reglas pricelist item | Estándar |
| Fechas vigencia | `date_start` / `date_end` en items | Estándar |
| Performance | Aceptable <10k reglas; indexación Odoo | Ver `PERFORMANCE.md` |

---

## 6–15. Áreas auditadas

Ver documentos especializados:

| Doc | Contenido |
|-----|-----------|
| `SALES_FLOW.md` | Cotización → factura → PDF |
| `PURCHASE_FLOW.md` | PO USD/DOP → factura → pago |
| `ACCOUNTING_FLOW.md` | Asientos, FX, conciliación |
| `EXCHANGE_RATE_FLOW.md` | Tasas, congelamiento, APIs |
| `PDF_FLOW.md` | Presentación moneda en documentos |
| `FISCAL_IMPACT.md` | NCF, DGII 606–609, 623 |
| `PERFORMANCE.md` | Impacto listas/tasas |
| `RECOMMENDATIONS.md` | Mejoras priorizadas |
| `ARCHITECTURE.md` | Estándar corporativo |

---

## Respuestas concretas (14 preguntas)

### 1. ¿Cómo maneja realmente Odoo los productos multimoneda?

No almacena el producto en dos monedas. El maestro está en **moneda funcional (DOP)**. La multimoneda comercial se logra con **listas de precios** cuya moneda define la moneda del pedido/factura. La pestaña Precios del producto refleja reglas por lista, no contradice `list_price`.

### 2. ¿Dónde se administra la tasa?

**Contabilidad → Configuración → Monedas → [USD] → Tasas**, o API/modelo `res.currency.rate`. En facturas: campo `invoice_currency_rate` (visible en formulario venta vía `hellenia_ux`).

### 3. ¿Qué ocurre si cambia la tasa mañana?

Las **nuevas** cotizaciones/pedidos usan la nueva tasa. Documentos ya confirmados mantienen su moneda; facturas publicadas mantienen tasa congelada.

### 4. ¿Qué ocurre con una cotización creada ayer?

La cotización conserva `currency_id` y precios calculados al crear/actualizar. Si se confirma hoy, la tasa puede recalcularse al convertir a factura según fecha factura (comportamiento Odoo 19 en conversión SO→INV).

### 5. ¿Qué ocurre con una factura ya publicada?

**Inmutable** en montos y tasa (`invoice_currency_rate`). Cambios de tasa del mercado no alteran asientos posted. Solo afectan pagos/conciliaciones posteriores.

### 6. ¿Cómo calcula Odoo la diferencia cambiaria?

Al conciliar pago con factura (moneda distinta o misma moneda con tasa distinta), Odoo compara:
- `amount_currency` pendiente en moneda documento
- Valor en moneda compañía al tipo de cambio del pago vs. el de la factura

Genera asiento en diario **CAMBI** con ganancia (ingreso FX) o pérdida (gasto FX).

### 7. ¿Dónde termina ese asiento?

Diario **CAMBI** (Exchange Difference), cuentas configuradas en compañía:
- Ingreso: `410500` Ingresos por diferencia cambiaria
- Gasto: `640101` ⚠️ actualmente "Cargos por servicios bancarios" post-COA-2

### 8. ¿Qué pasa con los pagos parciales?

Cada aplicación parcial reconcilia proporcionalmente. FX se calcula **por porción conciliada**. Múltiples pagos pueden generar múltiples asientos FX pequeños.

### 9. ¿Cómo se comporta la conciliación bancaria?

Extracto en moneda del diario (BNKD=DOP, BNKU=USD). Líneas deben coincidir moneda del movimiento. Conciliación cross-currency pasa por wizard de pago/registro con conversión automática.

### 10. ¿Qué pasa con los reportes financieros?

Balance, P&G y Mayor se presentan en **moneda compañía (DOP)**. Montos en moneda extranjera se convierten al cierre o al tipo histórico según configuración Odoo EE (account_reports). CxC/CxP aging usan `amount_residual` en moneda documento + equivalente funcional.

### 11. ¿Existe riesgo fiscal vendiendo en USD?

**Bajo-medio.** NCF no depende de moneda. DGII 607 exporta montos `*_signed` (equivalente DOP). Riesgo: contador espera ver montos originales USD en algún soporte — no en archivo 607 estándar. DGII 609 sí exige moneda y tasa para servicios exterior.

### 12. ¿Existe riesgo contable?

**Medio.** Principal riesgo: mapeo cuenta pérdida FX a 640101 (gastos bancarios). Secundario: falta UAT factura USD → pago DOP → asiento FX verificado.

### 13. ¿Qué arquitectura recomendarías para TODOS los clientes Justech?

**DOP funcional + listas comerciales USD/EUR + tasas centralizadas + diarios BNK por moneda + FX Odoo estándar.** Ver `ARCHITECTURE.md`.

### 14. ¿Qué modificarías antes del Go Live?

Ver `RECOMMENDATIONS.md` — ítems críticos:
1. Crear y certificar lista USD + asignación por segmento cliente
2. Corregir/validar cuenta pérdida cambiaria con contador
3. UAT E2E multimoneda documentado
4. Política de actualización de tasas (manual BCRD)
5. Mejoras PDF (tasa + equivalente DOP opcional)

---

## Estado certificación MC-1

| Gate | Resultado |
|------|-----------|
| Auditoría técnica | ✅ Completada |
| Implementación | ❌ No autorizada (MC-1) |
| Listo Go Live multimoneda | ⚠️ **Condicionado** a RECOMMENDATIONS críticas |

---

## Evidencia consultada

- `custom/hellenia_account/` — pagos BNKD/BNKU
- `custom/justech_l10n_do_reports/` — DGII 606/607/609
- `custom/justech_report_design/` — PDF moneda
- `config/company/` — golden config DOP
- `docs/COMMERCIAL_CONFIGURATION.md`, `ERP_FINANCIAL_ARCHITECTURE.md`
- `evidence/accounting-total-audit-readonly/prod.json`
- `evidence/phase24-1g-audit/` — PDF USD PASS
