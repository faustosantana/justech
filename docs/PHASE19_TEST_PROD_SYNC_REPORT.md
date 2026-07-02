# Fase 19 — Reporte de sincronización TEST → PRODUCCIÓN

**Fecha:** 2026-07-01  
**Resultado:** **PROD PASS**

---

## Resultado

| Campo | Valor |
|-------|-------|
| **PROD** | **PASS** |
| Commit promovido | `acf21ca` (`acf21caf43fd32a088e012b2008db6d53bb7a759`) |
| Commit base certificado | `bbaf113` (Fase 18.13) |
| Backup usado | `/opt/odoo-projects/hellenia/backups/hellenia-prod/2026-07-01_1059` |
| Rollback disponible | **SÍ** |

```bash
bash /opt/odoo-projects/hellenia/scripts/restore-hellenia-prod.sh \
  /opt/odoo-projects/hellenia/backups/hellenia-prod/2026-07-01_1059
```

---

## Módulos actualizados

| Módulo | Versión PROD anterior | Versión PROD actual | Acción |
|--------|----------------------|---------------------|--------|
| `hellenia_account` | 19.0.1.0.18 | **19.0.1.0.19** | upgrade |
| `hellenia_ui` | 19.0.1.0.4 | 19.0.1.0.4 | upgrade (sin cambio versión) |
| `hellenia_reports` | 19.0.1.0.1 | 19.0.1.0.1 | upgrade (sin cambio versión) |
| `justech_l10n_do_base` | 19.0.1.3.0 | 19.0.1.3.0 | upgrade (sin cambio versión) |
| `justech_l10n_do_ncf` | 19.0.1.4.0 | 19.0.1.4.0 | upgrade (sin cambio versión) |
| `justech_l10n_do_reports` | **19.0.1.2.0** | **19.0.1.12.1** | upgrade |

---

## Diferencias corregidas

1. **Pagos y retenciones** — flujo nativo Odoo 19 con `hellenia.payment.withholding.line` persistente, `hellenia_applied_amount` siempre guardado, parcial con `custom_user_amount`.
2. **Wizard de pagos** — selector catálogo retenciones en `account.payment.register` y wizard Clientes/Proveedores.
3. **Reporte 623** — exportador, menú, stamp gov post-reconcile.
4. **Menús DGII** — 606, 607, 608, 623 activos y accesibles.
5. **Bancos y métodos** — BNKD/BNKU/CSH1 con métodos en español vía `post_init_hook`.
6. **PDF** — layout `external_layout_hellenia` verificado.
7. **Vistas contables** — sin errores OWL en formularios de pago y factura.

---

## Errores encontrados y resolución

| # | Etapa | Error | Resolución |
|---|-------|-------|------------|
| 1 | Primer intento | `payment_setup.xml` ParseError en install | XML vacío + `post_init_hook` |
| 2 | Primer intento | `_compute_validation_state` faltante | Método implementado en `fiscal_report.py` |
| 3 | Healthcheck | Período DGII día 1 del mes | Fix `healthcheck-odoo.py` (fin de mes) |

**No se aplicaron parches manuales en PROD.** Todos los fixes certificados en TEST antes de re-promoción.

---

## Procedimiento ejecutado

1. ✓ Auditoría paridad TEST vs PROD (`phase19-test-prod-parity-audit.py`)
2. ✓ Identificación commit `acf21ca` (bbaf113 + fixes)
3. ✓ Backup completo PROD (`2026-07-01_1059`)
4. ✓ Verificación backup + manifest pre-promoción
5. ✓ Checkout commit certificado en VPS
6. ✓ Sync `custom/` desde repo
7. ✓ Upgrade 6 módulos objetivo
8. ✓ Reinicio Odoo PROD
9. ✓ Validación post-sync (23/23 PASS)
10. ✓ Healthcheck completo (PASS tras fix período)
11. ✓ Smoke login HTTPS 200

---

## Validación PROD

| Check | Resultado |
|-------|-----------|
| Login | PASS (HTTP 200) |
| Contabilidad | PASS |
| Pagos | PASS |
| Pago parcial | PASS |
| Retenciones | PASS |
| Reporte 606 | PASS |
| Reporte 607 | PASS |
| Reporte 608 | PASS |
| Reporte 623 | PASS |
| Factura / NCF | PASS |
| PDF | PASS |
| Menús | PASS |
| Logs sin errores | PASS |

**Validación automatizada:** `scripts/phase19-prod-post-sync-validation.py` — 23/23 PASS  
**Certificación TEST previa:** `phase18-13-final-payment-retention-test.py` — 89/89 PASS

---

## Evidencia

| Archivo | Descripción |
|---------|-------------|
| `evidence/phase19-test-prod-sync.json` | Resultado consolidado Fase 19 |
| `evidence/phase19-parity-audit.json` | Auditoría paridad pre/post |
| `evidence/phase18-13-final-payment-retention-test.json` | Certificación TEST 89/89 |
| `evidence/healthcheck-prod-2026-07-01_1101.json` | Healthcheck PROD final |

---

## Restricciones respetadas

- ✓ Sin cambios manuales en producción
- ✓ Sin tocar `odoo-pecv`
- ✓ Sin promover commits no certificados (acf21ca re-certificado 89/89 en TEST)
- ✓ Rollback disponible sin ejecutar

---

## Conclusión

**PRODUCCIÓN sincronizada con TEST.** Funcionalidad de localización dominicana Justech, pagos, bancos, retenciones, reportes DGII (606/607/608/623), wizard de pagos, PDF y menús contables operativos en `hellenia_prod`.
