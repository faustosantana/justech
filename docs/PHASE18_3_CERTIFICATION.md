# Fase 18.3 — Certificación final motor retenciones RD

**Rama:** `cursor/phase18-3-withholding-certification-dd85`  
**Ambiente:** `hellenia_test` exclusivamente  
**Script:** `scripts/phase18-3-certify-withholding-test.py`  
**Deploy:** `scripts/run-phase18-3-certify-test.sh`

---

## Objetivo

Auditoría funcional real de los 22 puntos obligatorios. No se asume PASS por existencia de código.

---

## Checklist certificado

| # | Verificación | Método |
|---|--------------|--------|
| 1 | Catálogo muestra retenciones activas | Query + HTML evidencia |
| 2 | Crear retención | `Catalog.create()` en savepoint |
| 3 | Editar retención | Write notas |
| 4 | Desactivar | `active=False` |
| 5 | Desactivada desaparece del selector | Dominio `_domain_for_payment` |
| 6 | Reactivada reaparece | `active=True` |
| 7 | Filtros cliente/proveedor/venta/compra | Dominio por operación |
| 8 | Múltiples retenciones misma factura | 2 catálogos en línea |
| 9 | Retenciones distintas por factura | Wizard multi-línea |
| 10 | Cálculo sobre base configurada | ITBIS base vs detalle |
| 11 | Recálculo retención tiempo real | Cambio `amount_to_pay` |
| 12 | Recálculo neto tiempo real | `amount_after_withholding` |
| 13 | Asientos contables | `account.payment.move_id` |
| 14 | Cuentas configuradas | Match `catalog.account_id` |
| 15 | Asiento balanceado | D = C |
| 16 | Conciliación bancaria | BNKD con cuenta |
| 17 | Reportes 606/607 | Facturas en reporte tras pago |
| 18 | Historial factura | Pago conciliado |
| 19 | Historial pago | Línea retención en asiento |
| 20 | Sin inglés | Scan vistas/menús |
| 21 | Sin códigos técnicos usuario | Nombres catálogo + arch wizard |
| 22 | Estilo Odoo/Hellenia | Widgets nativos + menú RD |

---

## Evidencia generada

| Archivo | Contenido |
|---------|-----------|
| `evidence/phase18-3/phase18-3-withholding-certification-test.json` | Resultado JSON completo |
| `evidence/phase18-3/01-catalogo-activo.html` | Captura visual catálogo |
| `evidence/phase18-3/07-selector-filtros.html` | Filtros selector |
| `evidence/phase18-3/17-reportes-fiscales.html` | 606/607 |
| `evidence/phase18-3/18-19-historial.html` | Trazabilidad factura/pago |
| `evidence/phase18-3/22-estilo-odoo.html` | UI nativa |

---

## Resultado certificación TEST

| Métrica | Valor |
|---------|-------|
| **Veredicto** | **PASS** |
| Checks | **23 / 23** |
| Módulo | `hellenia_account` **19.0.1.0.7** |
| Base de datos | `hellenia_test` |
| Timestamp UTC | 2026-06-30T20:50:00Z |
| Producción | **NO promover sin aprobación explícita** |

### Regresión

| Suite | Resultado | Notas |
|-------|-----------|-------|
| Fase 18.2 catálogo | PASS 23/23 | `phase18-2-regression.json` |
| Fase 17.4 wizard | 17/18 | Falla `withholdings_section`: test legado pre-Fase 18 (retenciones ahora por factura, no por pago) |

### Cuentas contables verificadas

| Retención | Cuenta TEST |
|-----------|-------------|
| RET-GOB-5 | 11080302 |
| RET-ITBIS-30 / 100 | 21030201 |
| RET-INF-ISR-10 | 21030301 |
| RET-INF-ITBIS-75 | 21030205 |
| RET-ISR-2 | 21030308 |
| RET-HON-10 | 21030302 |

### Selector verificado

- **Cobro cliente:** 5 retenciones (GOB, ITBIS 30/100, ISR 2%, Honorarios)
- **Pago proveedor:** 6 retenciones (informales + ITBIS + ISR 2% + Honorarios)

---

## Ejecución TEST

```bash
cd /opt/odoo-projects/hellenia
git checkout cursor/phase18-3-withholding-certification-dd85
./scripts/run-phase18-3-certify-test.sh
```

---

## Producción

**NO promover** sin aprobación explícita y backup PROD.
