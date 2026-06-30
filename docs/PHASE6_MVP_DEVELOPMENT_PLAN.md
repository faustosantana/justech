# Fase 6 — Plan de desarrollo MVP localización dominicana Justech

**Cliente:** Hellenia, S.R.L.  
**Ambiente:** `hellenia_dev` — https://dev.hellenia.cloud  
**Rama Git:** `feature/justech-l10n-do-mvp`  
**Fecha:** 2026-06-30  
**Estado:** **Completado (MVP)** — validado en DEV real (`hellenia_dev` @ `2.25.69.179`)

**Backup pre-instalación:** `/opt/odoo-projects/hellenia/backups/dev/2026-06-30_1122` — verificado (`verify-backup-dev.sh` PASS)

Construir el **MVP mínimo funcional** para que Hellenia pueda operar con **NCF tradicional** y **reportes fiscales básicos** (606/607/608), sin tocar core, Enterprise ni módulos oficiales.

El NCF actúa como **capa fiscal sobre la contabilidad estándar** (`account.move`, pagos, conciliaciones, CxC, CxP, inventario e impuestos).

---

## 2. Alcance MVP (desarrollado)

| Módulo | Responsabilidad |
|--------|-----------------|
| `justech_l10n_do_base` | Tipos documento fiscal, RNC, configuración compañía/diario |
| `justech_l10n_do_ncf` | Rangos NCF, consumo, asignación automática, validaciones, PDF |
| `justech_l10n_do_reports` | Reportes DGII 606/607/608 básicos, wizard período, export CSV/Excel |

### Tipos NCF cubiertos

| Prefijo | Uso MVP |
|---------|---------|
| B01 | Factura crédito fiscal (cliente con RNC) |
| B02 | Factura consumo final |
| B03 | Nota de débito (resolución automática vía `debit_origin_id`) |
| B04 | Nota de crédito |
| B11 | Comprobante de compras |
| B13 | Gastos menores |

---

## 3. Fuera de alcance (no desarrollado)

- `justech_l10n_do_pos`
- `justech_l10n_do_dgii` / Web Services DGII
- `justech_l10n_do_infile` / Infile
- eNCF (serie E)
- POS, terceros, licencia Enterprise
- TEST y PRODUCCIÓN

---

## 4. Orden de ejecución realizado

| Paso | Acción | Resultado |
|------|--------|-----------|
| 1 | Backup DEV real | `/opt/odoo-projects/hellenia/backups/dev/2026-06-30_1122` — verificado |
| 2 | Rama `feature/justech-l10n-do-mvp` | Creada y pusheada |
| 3 | Desarrollo `justech_l10n_do_base` | Manifest, security, models, views, data, tests, README |
| 4 | Instalación + validación base en DEV | `installed` — 3 tests unitarios PASS |
| 5 | Desarrollo `justech_l10n_do_ncf` | Rangos, consumo, `account.move`, PDF, 8 tests |
| 6 | Instalación + validación NCF en DEV | `installed` — tests PASS |
| 7 | Desarrollo `justech_l10n_do_reports` | 606/607/608, wizard, export, 2 tests |
| 8 | Instalación + validación reports en DEV | `installed` — tests PASS |
| 9 | Validación E2E `validate-phase6-mvp.py` | `PHASE6_MVP ok: true` |

Instalación **incremental** (no los tres módulos juntos sin validar por etapa), según instrucción del cliente.

---

## 5. Arquitectura técnica

```
justech_l10n_do_base
    ├── justech.do.fiscal.document.type   (B01–B04, B11, B13)
    ├── res.company.justech_do_fiscal_enabled
    ├── res.partner (RNC básico)
    └── account.journal (use_ncf, tipos permitidos)

justech_l10n_do_ncf  (depends: base + account_debit_note)
    ├── justech.do.ncf.range            (rangos, estados, consumo)
    ├── justech.do.ncf.consumption      (auditoría)
    └── account.move                    (NCF, asignación en action_post)

justech_l10n_do_reports  (depends: ncf)
    ├── justech.do.fiscal.report        (606/607/608)
    ├── justech.do.fiscal.report.line
    └── wizard período + export CSV/XLSX
```

### Flujo NCF en facturación

1. Usuario confirma factura (`action_post`).
2. `_justech_assign_ncf_before_post()` resuelve tipo documento (B01/B02/B04/B11/B13).
3. Busca rango activo (`_find_active_range`) con prioridad por diario.
4. Consume secuencia, registra auditoría, valida duplicados/formato.
5. Contabilidad estándar continúa sin asientos manuales adicionales.

---

## 6. Infraestructura DEV

**Cambio docker-compose** (`docker/dev/docker-compose.yml`):

```yaml
- ${CUSTOM_ADDONS_PATH:-../../custom}:/opt/odoo/custom:ro
```

Permite iterar módulos custom sin rebuild de imagen.

**Scripts operativos:**

| Script | Uso |
|--------|-----|
| `scripts/install-phase6-mvp-module.sh dev <modulo>` | Instalación incremental con `--test-enable` |
| `scripts/validate-phase6-mvp.py` | Validación E2E vía `odoo shell` |

---

## 7. Seguridad y convenciones Odoo 19

- Grupos vía `res.groups.privilege` + `privilege_id` (no `category_id` deprecado).
- Solo código en `custom/` con prefijo `justech_`.
- Herencia `_inherit` — sin modificar core ni Enterprise.

---

## 8. Pruebas planificadas vs ejecutadas

| Caso | Unit tests | E2E DEV |
|------|------------|---------|
| Factura B01 | ✅ | ✅ |
| Factura B02 | ✅ | ✅ |
| Nota crédito B04 | ✅ | ✅ |
| Compra B11 | ✅ | ✅ |
| Gasto menor B13 | ✅ | ✅ |
| Rango agotado | ✅ | ✅ |
| Rango vencido | ✅ | ✅ |
| NCF duplicado | ✅ | ✅ |
| Reporte 606 | — | ✅ |
| Reporte 607 | ✅ | ✅ |
| Reporte 608 | ✅ | ✅ |
| PDF con NCF | — | ✅ |
| Asiento balanceado | — | ✅ |
| CxC (línea receivable) | — | ✅ |
| CxP explícita | — | ⚠️ implícito vía compras |
| ITBIS explícito | — | ⚠️ implícito (118 = 100 + 18%) |
| Nota débito B03 | lógica en código | ⚠️ no E2E en script |

Detalle completo: [PHASE6_TEST_RESULTS.md](PHASE6_TEST_RESULTS.md)

---

## 9. Brechas conocidas (MVP)

1. Reportes 606/607/608 son **básicos** — no replican formato TXT oficial DGII ni todas las columnas normativas.
2. B03 (nota débito) tiene resolución en código pero **sin prueba E2E dedicada** en el script de validación.
3. Compras con NCF manual de proveedor: validación de formato existe; flujo operativo completo pendiente de UAT con Hellenia.
4. Export Excel requiere `xlsxwriter`; si no está instalado, cae a CSV.
5. Sin integración DGII, eNCF, Infile ni POS.

---

## 10. Próximos pasos (post-MVP)

1. UAT con Hellenia: rangos NCF reales autorizados por DGII.
2. Formato oficial DGII para 606/607/608 (TXT, validaciones normativas).
3. Módulo `justech_l10n_do_dgii` (envío WS) — Fase posterior.
4. eNCF / Infile — fuera de Etapa 1.
5. Promoción a TEST tras aprobación explícita (no automática).

---

## 11. Referencias

- [PHASE6_TEST_RESULTS.md](PHASE6_TEST_RESULTS.md)
- [JUSTECH_L10N_DO_MVP_RELEASE_NOTES.md](JUSTECH_L10N_DO_MVP_RELEASE_NOTES.md)
- [DGII_FISCAL_ARCHITECTURE.md](DGII_FISCAL_ARCHITECTURE.md)
- Evidencia: `evidence/phase6-mvp-validation.json`
