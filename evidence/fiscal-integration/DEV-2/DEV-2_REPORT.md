# Iteración DEV-2 — Reports DGII en erp.justech.do

| Campo | Valor |
|-------|-------|
| **Iteración** | DEV-2 (Reports read-only) |
| **Fecha** | 2026-07-09 |
| **BD** | `justech_dev` @ erp.justech.do |
| **Backup** | `/opt/odoo-dev/backups/fiscal-integration-dev2-20260709_215513` |
| **Resultado** | **PASS** |

## Fix aplicado en código fuente

**Problema:** dependencia circular XML — acciones en `fiscal_report_views.xml` y `dgii_report_review_views.xml` referenciaban vistas del otro archivo antes de cargarse.

**Solución (repo, no parche manual):**
1. Extraer acciones a `views/fiscal_report_actions.xml`
2. Orden manifest: vistas → acciones → wizards → menú
3. Quitar dependencia dura `hellenia_account` (623 con guards opcionales)

## Reinstalación limpia (post-fix)

| Paso | Resultado |
|------|-----------|
| Uninstall `justech_l10n_do_reports` | ✅ uninstalled |
| Install `-i justech_l10n_do_reports` | ✅ sin ParseError |
| Versión | 19.0.1.14.0 |

## Stack fiscal

| Módulo | Versión | Estado |
|--------|---------|--------|
| `l10n_do_accounting` (Adel) | 19.0.1.0.0 | ✅ activo |
| `justech_l10n_do_base` | 19.0.1.6.0 | ✅ installed |
| `justech_l10n_do_ncf` | 19.0.2.1.0 | ✅ installed, **inactivo** |
| `justech_l10n_do_reports` | 19.0.1.14.0 | ✅ installed |

| Control | Valor |
|---------|-------|
| `justech_do_fiscal_enabled` | **false** en 4 empresas |
| Diarios `justech_do_use_ncf` | **0** |
| NCF Adel histórico | **1.504** (Δ=0) |
| NCF Justech posted | **0** |

## Validaciones

| Script | Resultado |
|--------|-----------|
| `fiscal-integration-dev1-post-validate.py` | ✅ ok |
| `fiscal-integration-dev2-reports-smoke.py` | ✅ ok |
| `fiscal-integration-dev1-validate-full.py` | ✅ 19/19 PASS |

| Métrica | Pre | Post | Δ |
|---------|:---:|:----:|:-:|
| Asientos posted | 2.255 | 2.255 | 0 |
| NCF Adel | 1.504 | 1.504 | 0 |
| Conciliaciones | 947 | 947 | 0 |
| Pagos activos | 677 | 677 | 0 |
| GL balanceado | ✅ | ✅ | — |

### 606/607 read-only

| Métrica | Valor |
|---------|-------|
| Movimientos elegibles 606 | 763 |
| Movimientos elegibles 607 | 741 |
| Exporters 606/607 | ✅ |
| Wizard 606/607 | ✅ instanciable |

## Evidencias

| Archivo | Descripción |
|---------|-------------|
| `baseline_pre_reinstall.json` | Snapshot antes de reinstall |
| `install_reinstall.log` | Log instalación limpia |
| `post_validate.json` | Integridad histórica |
| `reports_smoke.json` | Smoke 606/607 |
| `validate_full_post_dev2.json` | 19 checks regresión |
| `validate_full_post_dev2.html` | Reporte visual |
| `screenshots/02_validate_full_post_dev2.png` | Captura |

## Riesgos

| Riesgo | Estado |
|--------|--------|
| Circular XML en install | ✅ Resuelto en source |
| hellenia_account ausente en dev | ✅ Guards en 623 |
| Activación accidental Justech NCF | Mitigado (SQL false) |

## Restricciones respetadas

- ❌ justgroup.app · ❌ Activar NCF Justech · ❌ Desinstalar Adel · ❌ merge

## Siguiente paso (DEV-3)

Generar 606/607 de periodo cerrado (export TXT, sin envío DGII) y evaluar piloto 1 empresa.
