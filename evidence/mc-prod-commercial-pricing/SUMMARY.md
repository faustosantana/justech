# MC-PROD — SUMMARY

**Fecha:** 2026-07-07T15:41:32Z  
**Entorno:** hellenia_prod — https://odoo.hellenia.cloud  
**Módulo:** `justech_multicurrency` v19.0.2.0.0  
**Veredicto:** **PASS**

**Backup:** `/opt/odoo-projects/hellenia/backups/hellenia-prod/mc-prod-2026-07-07_113725`

---

## Respuestas ejecutivas

1. ¿Módulo instalado en PROD? **SÍ** — v19.0.2.0.0
2. ¿Política USD/DOP configurada? **SÍ** — contable DOP, comercial USD, tasa 58
3. ¿Producto USD funciona? **SÍ** — 100 USD → list 5,800 DOP, cost 4,060 DOP, lista USD fixed 100
4. ¿Cotización USD funciona? **SÍ** — S00001, línea 100 USD
5. ¿Factura USD contabiliza en DOP? **SÍ** — INV/2026/00001, debit DOP 6,844, documento USD
6. ¿NCF/PDF siguen PASS? **SÍ** — NCF B0200009900, PDF 74,291 bytes
7. ¿Healthcheck PASS? **SÍ**
8. ¿Hay algún blocker? **NO**

---

## Despliegue ejecutado

| Fase | Resultado |
|------|-----------|
| Backup completo PROD | OK (8.1 MB dump verificado) |
| Instalar `justech_multicurrency` | OK |
| Configurar política comercial | OK |
| Smoke producto USD | OK |
| Smoke cotización + factura | OK |
| Validación post-despliegue | OK |
| Healthcheck PROD | PASS |

---

## Política comercial configurada

| Parámetro | Valor |
|-----------|-------|
| Moneda contable | DOP |
| Moneda comercial principal | USD |
| Clientes nuevos | USD |
| Proveedores nuevos | USD |
| Lista pública USD | Lista pública USD (id 8) |
| Tasa USD | 58 DOP/USD |

---

## Artefactos smoke PROD

| Artefacto | Valor |
|-----------|-------|
| Producto | `MC-PROD-USD-20260707154114` (id 14) |
| Cotización | S00001 (id 43) |
| Factura | INV/2026/00001 (id 201) |
| NCF | B0200009900 |

---

## Restricciones respetadas

- NCF: no modificado (solo asignación en factura smoke nueva)
- DGII: no tocado
- COA: 292 cuentas sin cambio
- PDFs: no modificados (solo render smoke)
- Asientos previos: 0 posted antes; +1 factura smoke

---

## Archivos evidencia

- `backup.md`
- `validation.json`
- `smoke_product.json`
- `smoke_sale_invoice.json`
- `healthcheck.json`
- `SUMMARY.md`

---

## Notas técnicas

- Scripts Odoo shell requieren `env.cr.commit()` explícito en PROD (workers activos).
- Sin commit, la política USD no persistía entre sesiones shell.
- Scripts locales actualizados; **sin commit git** (pendiente aprobación usuario).
