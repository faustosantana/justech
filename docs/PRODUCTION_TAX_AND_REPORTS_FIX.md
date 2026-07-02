# Fase 13.2 — Corrección fiscal y reportes en PRODUCCIÓN

**Fecha:** 2026-06-30 (UTC)  
**Entorno:** `hellenia_prod` — https://odoo.hellenia.cloud  
**Rama:** `cursor/fiscal-fix-phase13-2-dd85`  
**Backup previo:** `/opt/odoo-projects/hellenia/backups/hellenia-prod/2026-06-30_1558`

---

## Resumen ejecutivo

| Fase | Resultado |
|------|-----------|
| Diagnóstico inicial PROD | FAIL — impuesto 15%, plan `generic_coa` |
| Corrección en TEST | PASS |
| Certificación TEST | PASS |
| Backup PROD | OK |
| Corrección PROD | PASS |
| Validación PROD | PASS |
| **Estado final PROD** | **OPERATIVO — ITBIS 18%, sin 15%** |

---

## 1. Qué se corrigió

### Causa raíz (PROD inicial)

- BD `hellenia_prod` creada sin plan contable dominicano
- Plan `generic_coa` con 51 cuentas y 2 impuestos de venta/compra al **15%**
- XML IDs: `account.1_sale_tax_template`, `account.1_purchase_tax_template`
- Producto "Prueba" y defaults de compañía con 15%

### Acciones en PROD

1. **Backup** verificado (`2026-06-30_1558`)
2. **`fix-fiscal-rd-configuration.py`:**
   - Plan `do` cargado (288 cuentas)
   - Impuestos 15% **desactivados** (no eliminados — auditoría)
   - `account_sale_tax_id` → `18% ITBIS`
   - `account_purchase_tax_id` → `18% Cost Good`
   - 1 producto remapeado a ITBIS 18%
3. **Upgrade módulos** Justech → 19.0.1.2.0
4. **Traducciones** Fase 11 (`es_DO`) reaplicadas
5. **Secuencias PostgreSQL** corregidas preventivamente

### Código desplegado

- `justech_l10n_do_base` / `ncf` / `reports` v19.0.1.2.0
- Scripts de diagnóstico, corrección y validación
- Sin cambios en core, Enterprise, ni `odoo-pecv`

---

## 2. Qué se probó en TEST

Ver `docs/TAX_FIX_TEST_REPORT.md` — 13 escenarios PASS incluyendo:

- Cotización sin 15%
- B01, B02, B04, B11, B13
- Reportes 606/607/608
- PDF, anulación 608

Evidencia: `evidence/phase13-2-validate-test.json`

---

## 3. Qué se promovió a PRODUCCIÓN

| Componente | Versión / acción |
|------------|------------------|
| Plan contable | `do` (288 cuentas) |
| ITBIS venta default | 18% ITBIS |
| Impuesto 15% | Desactivado |
| justech_l10n_do_* | 19.0.1.2.0 |
| Reportes DGII español | Activo |
| Idioma | es_DO |

Evidencia post-fix:

- `evidence/phase13-2-fix-prod.json` — `ok: true`
- `evidence/phase13-2-diagnose-prod.json` — sin 15%, ITBIS 18%
- `evidence/phase13-2-validate-prod.json` — todos los escenarios PASS

---

## 4. Estado final PROD

| Verificación | Resultado |
|--------------|-----------|
| Impuesto 15% activo | **0** |
| ITBIS 18% en cotización nueva | **Sí** |
| Cuentas contables | 288 |
| Impuestos totales | 38 |
| Reportes 606/607/608 | Funcionales |
| Menú Reportes DGII | Español |
| Logs sin error crítico | Sí |
| odoo-pecv | Sin cambios |

---

## 5. Pendientes

| Ítem | Prioridad | Notas |
|------|-----------|-------|
| Rangos NCF operativos B01–B13 en PROD (datos Hellenia) | Alta | Validación creó rangos de prueba; configurar rangos DGII reales |
| Formato DGII exportación oficial | Media | TD-008 |
| Archivos `i18n/es.po` Justech | Baja | Textos ya en español en fuente |
| Secuencias PG en TEST | Baja | Aplicar `fix_seq.sql` en mantenimiento programado |

---

## 6. Recomendación

1. **Verificar manualmente** una cotización nueva en https://odoo.hellenia.cloud — debe mostrar **18% ITBIS**, no 15%.
2. **Configurar rangos NCF** de producción con secuencias DGII autorizadas.
3. **No reinstalar** módulos `l10n_do` en producción sin backup y ventana de mantenimiento.
4. Mantener flujo **TEST → validar → PROD** para futuros cambios fiscales.

---

## 7. Rollback

Si fuera necesario revertir:

```bash
/opt/odoo-projects/hellenia/scripts/restore-hellenia-prod.sh /opt/odoo-projects/hellenia/backups/hellenia-prod/2026-06-30_1558
```

Restaura PostgreSQL + filestore al estado pre-corrección.

---

**Certificación:** Fase 13.2 completada. Producción alineada con configuración fiscal dominicana y localización Justech en español.
