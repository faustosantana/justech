# MC-1 — Recomendaciones (sin implementación)

Priorizadas para convertir multimoneda en **estándar corporativo Justech** antes/después Go Live.

---

## 🔴 Crítico (bloqueante certificación Go Live multimoneda)

| ID | Recomendación | Acción | Owner |
|----|---------------|--------|-------|
| C1 | **UAT E2E multimoneda documentado** | SO USD → INV → NCF → PDF → PAY (USD y cross DOP) → verificar CAMBI | QA + Contador |
| C2 | **Lista de precios USD formal** | Crear "Lista pública USD", reglas, asignación partners export | Funcional |
| C3 | **Cuenta pérdida cambiaria** | Validar con contador: ¿640101 correcto o cuenta dedicada FX loss? | Contador |
| C4 | **Política tasa de cambio** | Frecuencia actualización, fuente (BCRD), responsable | Admin + Contador |
| C5 | **609 tasa obligatoria** | Vista/form factura compra exterior: `justech_do_foreign_exchange_rate` visible | Dev (post MC-1) |

---

## 🟠 Alto

| ID | Recomendación | Acción |
|----|---------------|--------|
| A1 | Golden config YAML | Agregar `pricelists.yaml` con DOP + USD templates |
| A2 | Partner defaults | Segmentar `property_product_pricelist` local vs export |
| A3 | Capacitación ventas | Documentar: list_price DOP ≠ precio USD comercial |
| A4 | DGII 607 conciliación | Procedimiento contador: PDF USD vs 607 DOP |
| A5 | Checklist go-live | Extender GO_LIVE con ítems MC-1 |
| A6 | Integración BCRD | Evaluar `currency_rate_live` o cron API Banco Central |

---

## 🟡 Medio

| ID | Recomendación | Acción |
|----|---------------|--------|
| M1 | PDF tasa + equivalente DOP | Factura USD muestra tasa y RD$ referencial |
| M2 | Alerta tasa stale | Notificación si USD sin tasa >3 días |
| M3 | Tests automatizados | Test USD invoice + FX reconcile en CI |
| M4 | Moneda proveedor default | `property_purchase_currency_id` en importadores |
| M5 | Dashboard FX | Vista moves CAMBI del mes |
| M6 | Audit trail tasas | Log cambios `res.currency.rate` vía justech audit |

---

## 🟢 Bajo

| ID | Recomendación | Acción |
|----|---------------|--------|
| B1 | EUR pricelist | Solo si cliente opera EU |
| B2 | Monto en letras PDF | Nice-to-have factura |
| B3 | POS multimoneda | Roadmap v1.1+ |
| B4 | Dual display cotización | USD + RD$ estimado |
| B5 | Archivo histórico tasas | Export anual CSV |

---

## Qué NO hacer

| Anti-recomendación | Razón |
|--------------------|-------|
| Cambiar company currency a USD | Rompe DGII/NCF/COA RD |
| Duplicar productos por moneda | Mantenimiento insostenible |
| Hardcodear tasas en precios | Pierde trazabilidad FX |
| Custom FX engine paralelo | Odoo CAMBI ya funciona |
| Ignorar 609 en compras exterior | Export FAIL |

---

## Roadmap sugerido post MC-1

```
MC-1  Auditoría (actual) ──► MC-2  Config golden USD
         │                           │
         │                           ▼
         │                      MC-3  UAT + certificación
         │                           │
         ▼                           ▼
    RECOMMENDATIONS              Go Live multimoneda
         │
         └──► MC-4  BCRD + PDF enhancements (v1.1)
```

---

## Estimación esfuerzo (orientativa)

| Fase | Esfuerzo | Dependencias |
|------|----------|--------------|
| MC-2 Config listas USD | 0.5–1 día | Decisión comercial Hellenia |
| MC-3 UAT FX | 1–2 días | Contador disponible |
| Cuenta FX fix | 0.5 día | Contador |
| PDF tasa (M1) | 1 día dev | MC-3 PASS |
| BCRD cron (A6) | 2–3 días dev | API BCRD estable |

---

## Aprobación requerida

Antes de implementar cualquier ítem:

1. Contador Hellenia — cuenta FX + tratamiento 607 USD
2. Dirección comercial — política listas USD
3. Justech producto — estándar `ARCHITECTURE.md` como baseline clientes RD

**MC-1 no autoriza implementación.** Solo esta lista priorizada.
