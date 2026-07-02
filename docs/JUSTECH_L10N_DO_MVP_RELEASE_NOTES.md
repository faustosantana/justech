# Justech l10n DO — Notas de release MVP (Fase 6)

**Versión:** 19.0.1.0.0  
**Fecha:** 2026-06-30  
**Rama:** `feature/justech-l10n-do-mvp`  
**Ambiente validado:** DEV (`hellenia_dev`)

---

## Resumen

Primera entrega funcional de la localización fiscal dominicana Justech para Hellenia. Permite operar **NCF tradicional (serie B)** y generar **reportes fiscales básicos** 606, 607 y 608, como capa sobre la contabilidad estándar de Odoo 19.

---

## Módulos incluidos

### `justech_l10n_do_base` (19.0.1.0.0)

- Tipos de documento fiscal: B01, B02, B03, B04, B11, B13
- Flag `justech_do_fiscal_enabled` en compañía
- Validación RNC básica en contactos
- Configuración fiscal en diarios contables
- Menú: Contabilidad → Justech RD → Tipos de documento

**Dependencias:** `account`, `contacts`, `l10n_do`

### `justech_l10n_do_ncf` (19.0.1.0.0)

- Rangos NCF autorizados (crear, activar, cancelar, agotar, vencer)
- Control de próximo número y auditoría de consumo
- Asignación automática al publicar:
  - B01 si cliente tiene RNC
  - B02 consumidor final
  - B04 notas de crédito
  - B03 notas de débito (si `debit_origin_id`)
  - B11/B13 en compras según diario
- Validaciones: formato, duplicados, rango vencido/agotado
- Anulación NCF (`action_void_ncf`) para reporte 608
- NCF visible en PDF de factura

**Dependencias:** `justech_l10n_do_base`, `account_debit_note`

### `justech_l10n_do_reports` (19.0.1.0.0)

- Reportes básicos DGII:
  - **606** — Compras
  - **607** — Ventas
  - **608** — NCF anulados
- Wizard de período
- Exportación CSV y Excel (XLSX si `xlsxwriter` disponible)

**Dependencias:** `justech_l10n_do_ncf`

---

## Instalación (DEV)

Orden obligatorio:

```bash
./scripts/install-phase6-mvp-module.sh dev justech_l10n_do_base
# validar

./scripts/install-phase6-mvp-module.sh dev justech_l10n_do_ncf
# validar

./scripts/install-phase6-mvp-module.sh dev justech_l10n_do_reports
# validar
```

Validación E2E:

```bash
docker compose --env-file config/dev/.env run --rm -T odoo odoo shell -d hellenia_dev \
  --db_host=db --db_user=odoo --db_password=odoo --no-http \
  < scripts/validate-phase6-mvp.py
```

Resultado esperado: `PHASE6_MVP ok: true`

---

## Configuración inicial

1. Activar **Fiscal RD (Justech)** en la compañía.
2. En diario de ventas: marcar **Usar NCF**, seleccionar tipos B01/B02/B04.
3. Crear rangos NCF activos por tipo y diario.
4. En diario de compras: configurar B11 y/o B13 según operación.
5. Publicar facturas — el NCF se asigna automáticamente.

---

## Archivos principales

```
custom/justech_l10n_do_base/
custom/justech_l10n_do_ncf/
custom/justech_l10n_do_reports/
scripts/install-phase6-mvp-module.sh
scripts/validate-phase6-mvp.py
docker/dev/docker-compose.yml          # volume custom addons
docs/PHASE6_MVP_DEVELOPMENT_PLAN.md
docs/PHASE6_TEST_RESULTS.md
evidence/phase6-mvp-validation.json
```

---

## Pruebas ejecutadas

- 13 tests unitarios (instalación)
- 14 casos E2E en DEV — todos PASS
- PDF factura con NCF renderizado (~31 KB)
- Asiento balanceado; CxC verificada

Ver [PHASE6_TEST_RESULTS.md](PHASE6_TEST_RESULTS.md).

---

## Limitaciones conocidas

- No incluye eNCF, Infile, Web Services DGII ni POS
- Reportes son **básicos** — no archivo TXT oficial para envío DGII
- B03 sin prueba E2E dedicada en script de validación
- Licencia Enterprise no registrada (entorno DEV)
- Solo validado en DEV; TEST/PROD no tocados

---

## Próxima versión (planificado)

- Formato DGII oficial 606/607/608
- UAT con rangos NCF reales Hellenia
- `justech_l10n_do_dgii` (envío electrónico)
- eNCF / Infile (etapas posteriores)

---

## Soporte

Documentación técnica: `custom/justech_l10n_do_*/README.md`  
Arquitectura fiscal: `docs/DGII_FISCAL_ARCHITECTURE.md`
