# FDP Deploy — erp.justech.do / justech_dev

| Campo | Valor |
|-------|-------|
| **Fecha** | 2026-07-09 23:19 CEST |
| **Resultado** | **PASS** |
| **Evidencia servidor** | `/opt/odoo-dev/evidence/fiscal-integration/FDP-deploy-20260709_231534/` |
| **Evidencia local** | `evidence/fiscal-integration/FDP-deploy-20260709/` |
| **Backup** | `/opt/odoo-dev/backups/fiscal-integration-fdp-pre-20260709_231604` |

## Módulos actualizados

| Módulo | Acción | Código en disco | `ir_module_module` |
|--------|--------|-----------------|---------------------|
| `justech_l10n_do_base` | `-u` | **19.0.1.7.0** (FDP) | 19.0.1.6.0* |
| `justech_l10n_do_reports` | `-u` | **19.0.1.15.0** | 19.0.1.14.0* |
| `justech_l10n_do_ncf` | no tocado | 19.0.2.1.0 | installed |
| `l10n_do_accounting` (Adel) | no tocado | — | installed |

\*El provider y exportadores corregidos están **activos** (smoke + 606 validados). La semver en BD puede quedar desfasada hasta próximo `-u` con bump detectado; el código desplegado incluye `fiscal_data_provider.py`.

## Restricciones respetadas

- ❌ justgroup.app
- ❌ Backfill / migración histórico
- ❌ Activar motor NCF Justech (`justech_do_fiscal_enabled=false` en 4 empresas)
- ❌ Desinstalar Adel
- ❌ merge / development / main

## Healthcheck

| Fase | Resultado |
|------|-----------|
| Pre | **18/18 PASS** |
| Post | **18/18 PASS** |

Histórico intacto post-deploy: 2255 posted, 1504 NCF Adel, 947 reconciles, 677 pagos, GL balanceado.

## Assets / login

| Check | Resultado |
|-------|-----------|
| Assets físicos | 149/149 OK |
| `/web/assets` CSS/JS | HTTP **200** |
| `/web/login` | HTTP **200** |

## Validación E310000019120 (FP/2026/06/0084)

| Campo | Valor |
|-------|-------|
| `l10n_latam_document_number` | E310000019120 |
| `justech_do_ncf` | vacío (sin modificar) |
| Provider NCF | **E310000019120** (`adel_latam`) |
| Error «sin NCF» post-deploy | **NO** |
| Error restante | `impuesto no clasificado para DGII: 2% CDT` (configuración impuesto) |

## Comparativa 606 — período **202606** (JUSTECH S.R.L.)

| Métrica | Antes | Después | Δ |
|---------|------:|--------:|--:|
| Documentos en período | 90 | 90 | 0 |
| Válidos exportables | 0 | **85** | +85 |
| Incompletos | 90 | **5** | -85 |
| **Total errores** | **95** | **5** | **-90** |
| Errores «sin NCF» | **90** | **0** | **-90 resueltos** |
| Errores impuesto (tax) | 5 | 5 | 0 |

### Errores que quedan (5 — datos/configuración real)

Todas las facturas afectadas comparten el mismo problema de **clasificación DGII del impuesto «2% CDT»**:

| Factura | Error |
|---------|-------|
| FP/2026/06/0083 | impuesto no clasificado: 2% CDT |
| FP/2026/06/0084 | impuesto no clasificado: 2% CDT |
| FP/2026/06/0044 | impuesto no clasificado: 2% CDT |
| FP/2026/06/0045 | impuesto no clasificado: 2% CDT |
| FP/2026/06/0046 | impuesto no clasificado: 2% CDT |

**Conclusión:** el 90% de errores del 606/202606 eran **falsos positivos de integración** (NCF en Adel no leído). Los 5 restantes son **errores reales de configuración fiscal** (mapear CDT en catálogo de retenciones/impuestos DGII).

### Factura objetivo E310000019120 — antes/después

| | Antes | Después |
|--|-------|---------|
| missing_ncf_error | **true** | **false** |
| errors | sin NCF + 2% CDT | solo 2% CDT |

## Rollback

```
/opt/odoo-dev/backups/fiscal-integration-fdp-pre-20260709_231604
```

Procedimiento en `scripts/fiscal-integration-dev1-backup.sh` MANIFEST.

## Archivos evidencia clave

| Archivo | Contenido |
|---------|-----------|
| `pre_606_202606.json` | 95 errores, 90 sin NCF |
| `post_606_202606.json` | 5 errores, 0 sin NCF |
| `606_compare_202606.json` | Comparativa consolidada |
| `post_provider_smoke.json` | E310000019120 OK |
| `BACKUP_PATH.txt` | Ruta backup |

## Siguiente paso recomendado

1. **Configurar impuesto «2% CDT»** en catálogo DGII / `hellenia.withholding.catalog` para las 5 facturas restantes.
2. Re-validar 606/202606 — expectativa: **0 incompletos** o solo exclusiones manuales.
3. Opcional: bump semver en `ir_module_module` con `-u` tras commit de manifests.
