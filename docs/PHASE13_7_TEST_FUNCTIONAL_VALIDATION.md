# Fase 13.7 — Validación funcional completa en TEST

**Fecha:** 2026-06-29  
**Ambiente:** `hellenia_test` / `https://test.hellenia.cloud`  
**Commit certificado:** `f918576`  
**Resultado:** **PASS**

---

## Política aplicada

Ningún cambio se aplicó en producción hasta completar esta validación. Producción (`odoo.hellenia.cloud`) permaneció en estado 404 documentado en `docs/ROOT_CAUSE_ANALYSIS_404.md`.

---

## Cambios desplegados en TEST

| Componente | Cambio |
|------------|--------|
| Traefik | Router HTTP con `.service` explícito + router WS `:8072` (paridad con PROD) |
| `config/test/odoo.conf` | `gevent_port = 8072` |
| `hellenia_base` | Logo oficial JPEG en `static/img/hellenia_logo.jpg` |
| Assets | Limpieza adjuntos huérfanos + regeneración bundles QWeb |
| Script | `scripts/phase13-7-validate-test.py` |

---

## Datos de prueba creados

| Entidad | Cantidad |
|---------|----------|
| Clientes | 10 |
| Proveedores | 5 |
| Productos | 20 |
| Existencias | Configuradas por producto |
| Rangos NCF | B01, B02, B03, B04 (prueba) |

---

## Flujo E2E ejecutado

| Paso | Resultado | Referencia |
|------|-----------|------------|
| Cotización | OK | S00016 |
| Confirmación pedido | OK | `sale` |
| Entrega | OK (assigned) | Picking validado |
| Factura cliente | OK | INV/2026/00119 |
| NCF factura | OK | B0100020001 |
| Cobro cliente | OK | PBNK1/2026/00104 |
| Nota crédito | OK | B0400020018 |
| Nota débito | OK | B0300020018 |
| Orden compra | OK | P00010 |
| Recepción | OK | `done` |
| Factura proveedor | OK | FACTU/2026/06/0105 |
| Pago proveedor | OK | PBNK1/2026/00105 |
| Reporte 606 | OK | `action_606_report` |
| Reporte 607 | OK | `action_607_report` |
| Reporte 608 | OK | `action_608_report` |
| PDF cotización | OK | attachment 81083 |
| PDF factura | OK | attachment 87347 |
| PDF nota crédito | OK | attachment 86028 |

---

## Validaciones transversales

| Área | Estado | Evidencia |
|------|--------|-----------|
| Contabilidad | PASS | Balance cuadra (`accounting_balance: true`) |
| Inventario | PASS | 16 quants con stock |
| Impuestos ITBIS 18% | PASS | `tax_18_sale: true` |
| NCF | PASS | Factura con NCF asignado |
| Módulo `hellenia_reports` | PASS | Instalado |
| Layout PDF corporativo | PASS | `hellenia_reports.external_layout_hellenia` |
| HTTP login TEST | PASS | `200` en `/web/login` |
| UX clientes/cotización | PASS | Sin `FileNotFoundError` tras fix assets |
| Branding logo | PASS | `res.company` con logo JPEG |

---

## Evidencia

- JSON: `evidence/phase13-7-test-functional-validation.json`
- Comando: `bash scripts/run-phase13-7-validate-test.sh`

---

## Conclusión

**TEST PASS** — El commit `f918576` está certificado para promoción a producción según `docs/PRODUCTION_PROMOTION_PLAN.md`, sujeto a aprobación explícita y backup previo.
