# Fase 18.2 — Validación TEST

**Rama:** `cursor/phase18-2-withholding-catalog-dd85`  
**Módulo:** `hellenia_account` 19.0.1.0.6  
**Script:** `scripts/phase18-2-validate-withholding-catalog-test.py`  
**Deploy:** `scripts/run-phase18-2-test.sh`  
**Evidencia:** `evidence/phase18-2-withholding-catalog-test.json`

---

## Casos de prueba (20 + UX)

| # | Caso | Criterio PASS |
|---|------|---------------|
| 01 | Catálogo completo | 7 retenciones activas RET-* |
| 02 | Crear desde admin | Nueva retención temporal |
| 03 | Editar cuenta | Write cuenta contable OK |
| 04 | Desactivar | No aparece en selector |
| 05 | Reactivar | Vuelve al selector |
| 06 | Cobro sin retención | Ninguna + pago OK |
| 07 | Cobro ITBIS 30% | Monto retenido > 0 |
| 08 | Cobro Gobierno 5% | Retención ISR gobierno |
| 09 | Cobro dos retenciones | ≥2 líneas detalle |
| 10 | Pago informal 10% | ISR proveedor informal |
| 11 | Pago ITBIS 75% | ITBIS informal |
| 12 | Pago dos retenciones | ≥2 líneas detalle |
| 13 | Asiento balanceado | D = C |
| 14 | Cuentas retención | Todas activas con cuenta |
| 15 | CxC | Impacto en cobro |
| 16 | CxP | Impacto en pago |
| 17 | Reporte 606 | Generación OK |
| 18 | Reporte 607 | Generación OK |
| 19 | Español | Menú y acción en español |
| 20 | Sin códigos técnicos | Nombres limpios |
| UX | Selector cliente | ≥4 retenciones incl. GOB-5 |
| UX | Selector proveedor | Informales + ITBIS |

---

## Regresión

Tras Fase 18.2 se ejecutan:

- `phase18-validate-withholding-test.py` (motor Fase 18)
- `phase17-4-validate-payment-wizard-test.py` (wizard RPC)
- `phase16-validate-payments-test.py` (pagos/bancos) — vía run script

---

## Despliegue TEST obligatorio

```bash
# En VPS TEST (/opt/odoo-projects/hellenia)
git fetch && git checkout cursor/phase18-2-withholding-catalog-dd85
./scripts/run-phase18-2-test.sh
```

Pasos internos del script:

1. `docker compose run odoo -u hellenia_account --stop-after-init`
2. `docker compose restart odoo` ← **obligatorio** (registry Python)
3. Shell Odoo con script de validación
4. Escritura de evidencia JSON

---

## Resultado

> Completar tras ejecución en VPS TEST con campo `ok: true` en evidencia.

| Métrica | Valor |
|---------|-------|
| TEST | PENDIENTE / PASS / FAIL |
| Passed | — |
| Failed | — |
| Producción | **NO promover sin aprobación explícita** |

---

## Causa raíz documentada

Solo aparecía «Retención 5% Gobierno» porque el dominio del selector filtraba `partner_scope=customer` y todas las demás retenciones tenían `partner_scope=supplier`. La corrección amplía alcance y añade filtro por operación (venta/compra).
