# Inventario Oficial de Módulos — Odoo 19 Enterprise

**Cliente:** Hellenia, S.R.L. — República Dominicana  
**Build:** Odoo `19.0-20260619` Enterprise On-Premise  
**Ambiente escaneado:** Contenedor `hellenia-dev-odoo-1` (VPS DEV)  
**Fecha inventario:** 2026-06-30  
**Método:** Escaneo de filesystem (`__manifest__.py`) — **no solo módulos instalados**

---

## Resumen ejecutivo

| Métrica | Valor | Evidencia |
|---------|------:|-----------|
| Módulos oficiales en tarball | **1.451** | `evidence/odoo19-module-inventory.json` |
| Community (`/usr/lib/python3/dist-packages/odoo/addons`) | **679** | JSON `summary.by_origin.community` |
| Enterprise (`/opt/odoo/enterprise/addons`) | **772** | JSON `summary.by_origin.enterprise` |
| Registrados en BD `hellenia_dev` | **1.457** | `ir_module_module` (incluye custom/stubs) |
| Instalados en BD | **108** | PostgreSQL query 2026-06-30 |
| `auto_install: true` | **725** | Manifest parse |
| `auto_install` condicional (lista `depends`) | **268** | Manifest parse |
| Categoría `Hidden` | **141–142** | Manifest `category` |
| Módulos `l10n_*` | **537** | `evidence/odoo19-l10n-modules.txt` |
| Módulos `Accounting/*` | **506–521** | Clasificación por categoría |
| Módulos fiscal flag (manifest) | **277** | Clasificación script |
| Módulos LATAM framework | **3** base + **9** dependientes | Ver sección LATAM |

**República Dominicana — módulos oficiales existentes en tarball:**

| Módulo | Origen | Licencia | `auto_install` | Estado BD `hellenia_dev` |
|--------|--------|----------|----------------|--------------------------|
| `l10n_do` | Community | LGPL-3 | `['account']` | **installed** |
| `l10n_do_reports` | Enterprise | OEEL-1 | `true` | **installed** |
| `l10n_do_check_printing` | Enterprise | OEEL-1 | `['l10n_do']` | **installed** |
| `l10n_do_edi` | — | — | — | **NO EXISTE** en tarball ni BD |
| `l10n_latam_base` | Community | LGPL-3 | `false` | uninstalled |
| `l10n_latam_invoice_document` | Community | LGPL-3 | `false` | uninstalled |
| `l10n_latam_check` | Community | LGPL-3 | `false` | uninstalled |

---

## Metodología (sin asumir)

### 1. Rutas de addons escaneadas

```
/opt/odoo/enterprise/addons          → Enterprise (OEEL-1)
/usr/lib/python3/dist-packages/odoo/addons → Community (LGPL-3)
```

Confirmado en log Odoo:
```
addons paths: ... '/opt/odoo/enterprise/addons', '/opt/odoo/custom', ...
```

### 2. Por cada módulo se extrajo de `__manifest__.py`

- `name`, `version`, `category`, `license`
- `depends`, `auto_install`, `application`, `installable`
- `external_dependencies`, `data`, `demo`
- Conteo de archivos: `models/`, `views/`, `wizard/`, `report/`, `security/`, `data/`, `csv/`, `xml/`

### 3. Búsqueda de keywords en contenido

Términos buscados (global y focalizado en `l10n_do*`):

`NCF`, `ncf`, `DGII`, `Fiscal`, `LATAM`, `l10n_latam`, `Dominican`, `República`,
`document_type`, `Invoice Document`, `Fiscal Localization`, `B01`–`B04`, `B11`, `B13`,
`E31`–`E34`, `606`, `607`, `608`, `l10n_do_edi`, `comprobante`, `ncf_sequence`

### 4. Estado en base de datos

```sql
SELECT name, state FROM ir_module_module
WHERE name IN ('l10n_do','l10n_do_reports','l10n_do_check_printing',
               'l10n_latam_base','l10n_latam_invoice_document','l10n_latam_check','l10n_do_edi');
```

### 5. Script reproducible

```bash
# En contenedor Odoo:
python3 scripts/generate-odoo19-module-inventory.py --output evidence/
```

---

## Artefactos de evidencia

| Archivo | Descripción | Tamaño aprox. |
|---------|-------------|---------------|
| `evidence/odoo19-module-inventory.json` | Inventario completo 1.451 módulos | 1.6 MB |
| `evidence/odoo19-all-modules.csv` | CSV tabular (1 fila/módulo) | 1.451 filas |
| `evidence/odoo19-enterprise-modules.txt` | Lista nombres Enterprise | 776 líneas |
| `evidence/odoo19-l10n-modules.txt` | Lista módulos `l10n_*` | 537 líneas |
| `evidence/odoo19-fiscal-deep-scan.json` | Deep scan fiscal/LATAM/l10n | 645 módulos |
| `scripts/generate-odoo19-module-inventory.py` | Script regeneración | — |

---

## Clasificación global

### Por origen y licencia

| Origen | Cantidad | Licencia típica |
|--------|----------|-----------------|
| Enterprise | 772 | OEEL-1 (754), OPL-1 (4) |
| Community | 679 | LGPL-3 (693 total LGPL) |

### Auto-install

| Tipo | Cantidad | Descripción |
|------|----------|-------------|
| `auto_install: true` | 725 | Se instala automáticamente cuando dependencias satisfechas |
| `auto_install: ['mod']` | 268 | Condicional — requiere módulo específico |
| Sin auto-install | ~458 | Instalación manual |

**Ejemplos RD:**

- `l10n_do`: `auto_install: ['account']` → se instala al configurar contabilidad con país DO
- `l10n_do_reports`: `auto_install: true` → se instala con `l10n_do` + `account_reports`
- `l10n_do_check_printing`: `auto_install: ['l10n_do']`

### Hidden (categoría manifest)

**141 módulos** con `category` que inicia en `Hidden` o `Hidden/Tests`.

Estos módulos existen en el tarball pero no aparecen en Apps por defecto. Incluyen bridges de test, módulos técnicos y dependencias internas.

### Localization (`l10n_*`)

**537 módulos** con prefijo `l10n_`. Subcategorías principales:

| Categoría manifest | Cantidad |
|------------------|----------|
| `Accounting/Localizations/Account Charts` | 120 |
| `Accounting/Localizations/Reporting` | 115 |
| `Accounting/Localizations/EDI` | 73 |
| `Accounting/Localizations` | 42 |

### Accounting

**506+ módulos** en categorías `Accounting/*` incluyendo:

- Core: `account`, `account_debit_note`, `account_check_printing`, `account_edi`, `account_edi_ubl_cii`
- Enterprise: `account_accountant`, `account_reports`, `account_asset`, `account_followup`, `account_budget`
- Localizaciones por país (ver CSV completo)

### Fiscal (flag en manifest/contenido)

**277 módulos** con referencias fiscales en manifest. **645 módulos** en deep scan fiscal/LATAM.

---

## Framework LATAM (Odoo 19)

### Módulos base LATAM (Community)

| Módulo | Propósito | `depends` | Modelos clave |
|--------|-----------|-----------|---------------|
| `l10n_latam_base` | Tipos de identificación (RNC/Cédula/etc.) | `contacts`, `base_vat` | `l10n_latam.identification.type` |
| `l10n_latam_invoice_document` | Tipos de documento fiscal LATAM | `account`, `account_debit_note` | `l10n_latam.document.type` |
| `l10n_latam_check` | Cheques LATAM | `account`, `base_vat` | — |

### Países que dependen de framework LATAM documentos

Solo **9 módulos** declaran dependencia directa de `l10n_latam_*`:

```
l10n_ar, l10n_ar_withholding, l10n_br, l10n_cl, l10n_co, l10n_ec, l10n_gt_edi, l10n_pe, l10n_uy
```

**`l10n_do` NO depende de `l10n_latam_*`** — confirmado en manifest y grep (`l10n_latam: 0 files in l10n_do*`).

### Módulos LATAM con EDI (74 `l10n_*_edi`)

Ejemplos con documentos fiscales completos (contraste con RD):

- `l10n_ar_edi`, `l10n_cl_edi`, `l10n_co_edi`, `l10n_ec_edi`, `l10n_mx_edi`, `l10n_pe_edi`, etc.

---

## República Dominicana — evidencia detallada

### `l10n_do` (Community, LGPL-3)

**Ruta:** `/usr/lib/python3/dist-packages/odoo/addons/l10n_do`

**Manifest `depends`:**
```python
'depends': ['account', 'base_iban'],
'auto_install': ['account'],
'data': ['data/account_tax_report_data.xml'],
```

**Árbol de archivos (completo — 17 archivos de código/datos):**

```
l10n_do/
├── __manifest__.py
├── models/template_do.py
├── data/
│   ├── account_tax_report_data.xml
│   └── template/
│       ├── account.account-do.csv      (289 cuentas)
│       ├── account.group-do.csv
│       ├── account.tax-do.csv          (37 impuestos)
│       ├── account.fiscal.position-do.csv
│       └── account.tax.group-do.csv
└── demo/demo_company.xml
```

**Lo que SÍ incluye:**
- Plan contable RD (NIIF/DGII)
- Impuestos ITBIS, retenciones ISR/ITBIS
- Posiciones fiscales
- Reporte impuestos ITBIS (casillas 2B11, 2B13 = **casillas formulario**, no tipos NCF)

**Lo que NO incluye (evidencia negativa):**
- Sin carpeta `models/` de documentos fiscales
- Sin `security/ir.model.access.csv`
- Sin `views/` de facturas/NCF
- Sin `wizard/` de emisión fiscal
- Sin archivos de secuencias NCF
- Sin `report/` de factura DGII

**Nota explícita del manifest:**
> *"Esta localización, aunque posee las secuencias para NCF, las mismas no pueden ser utilizadas sin la instalación de módulos de terceros o desarrollo adicional."*

### `l10n_do_reports` (Enterprise, OEEL-1)

**Ruta:** `/opt/odoo/enterprise/addons/l10n_do_reports`

**Manifest:**
```python
'depends': ['l10n_do', 'account_reports'],
'auto_install': True,
'data': [
    'data/account_return_data.xml',
    'data/profit_and_loss.xml',
    'data/balance_sheet.xml',
],
```

**Archivos:** 8 archivos (3 XML de reportes + i18n). **Sin** referencias a DGII, NCF, 606, 607, 608:

```
grep -rin "DGII|NCF|606|607|608" l10n_do_reports/ → NO MATCHES
```

Contiene: Balance General, Estado de Resultados, declaraciones (`account_return_data.xml`). **No** libros de compras/ventas DGII.

### `l10n_do_check_printing` (Enterprise, OEEL-1)

**Ruta:** `/opt/odoo/enterprise/addons/l10n_do_check_printing`

- `depends`: `account_check_printing`, `l10n_do`
- `models/`: `account_payment.py`, `company.py`
- `report/`: layouts de cheques DO
- Sin relación con NCF/e-CF

### `l10n_do_edi`

```
find addons -name "l10n_do_edi" → 0 results
ir_module_module WHERE name='l10n_do_edi' → NOT_IN_DB
grep -ril "l10n_do_edi" addons → 0 files
```

**Conclusión:** No existe módulo oficial `l10n_do_edi` en Odoo 19 build `20260619`.

---

## Matriz de búsqueda por keywords

### Escaneo global (todos los addons — 1.451 módulos)

| Término | Archivos con match | Interpretación |
|---------|-------------------:|----------------|
| `l10n_do_edi` | **0** | Módulo inexistente |
| `ncf_sequence` | **0** | Sin secuencias NCF en código |
| `DGII` | 71 | Mayoría en `l10n_do` manifest/CSV; no reportes 606-608 |
| `NCF` | 182 | Casi todo fuera de `l10n_do` (FR, IN, tests) |
| `l10n_latam.document` | 223 | Framework LATAM (AR, CL, CO, etc.) |
| `document_type` | 672 | Genérico + LATAM |
| `B01` | 136 | **Colombia DIAN**, Bélgica POS, Avatax — no RD |
| `B02` | 108 | Idem |
| `B11` | 204 | Casillas ITBIS RD + otros países |
| `E31`–`E34` | 85–113 | **Mongolia, Italia, Colombia** — no RD |
| `606` | 546 | Cuentas contables `61060600` + otros |
| `607` | 491 | Cuenta `61060700` + otros |
| `608` | 524 | Otros países/contextos — **0 en l10n_do*** |

### Escaneo focalizado (`l10n_do*` únicamente — 3 módulos)

| Término | Archivos | Archivo / contexto |
|---------|----------|-------------------|
| `NCF` | **1** | `l10n_do/__manifest__.py` (solo descripción) |
| `ncf` | **1** | Idem |
| `DGII` | **2** | `__manifest__.py`, `account.account-do.csv` |
| `B11` | **1** | `account_tax_report_data.xml` — casilla ITBIS `2B11` |
| `B13` | **1** | `account_tax_report_data.xml` — casilla ITBIS `2B13` |
| `606` | **1** | `account.account-do.csv` — cuenta `61060600` Promociones (**falso positivo**) |
| `607` | **1** | `account.account-do.csv` — cuenta `61060700` Restaurantes (**falso positivo**) |
| `608` | **0** | — |
| `B01`, `B02`, `B03`, `B04` | **0** | Tipos NCF ausentes |
| `E31`, `E32`, `E33`, `E34` | **0** | e-CF ausentes |
| `l10n_latam` | **0** | Sin integración framework LATAM |
| `document_type` | **1** | `account.tax-do.csv` (campo genérico impuesto) |

**Evidencia grep 606/607 en l10n_do:**
```
account.account-do.csv:262: "l10n_do_61060600","61060600","Promotions"
account.account-do.csv:263: "l10n_do_61060700","61060700","Restaurant Expenses"
```

**Evidencia grep B11/B13 en l10n_do:**
```
account_tax_report_data.xml:121: <record id="account_tax_report_2B11_base" ...>
account_tax_report_data.xml:145: <record id="account_tax_report_2B13_base" ...>
```

---

## Estructura por tipo de archivo — `l10n_do` vs peer LATAM

| Componente | `l10n_do` | `l10n_latam_invoice_document` | `l10n_cl_edi` (referencia) |
|------------|-----------|-------------------------------|----------------------------|
| `models/` | 1 (`template_do.py`) | 6+ (`l10n_latam_document_type.py`, etc.) | 20+ |
| `views/` | 0 | 5 | 10+ |
| `wizard/` | 0 | 1 (`account_move_reversal`) | varios |
| `security/` | 0 | 1 (`ir.model.access.csv`) | sí |
| `report/` | 0 (solo tax report data) | 2 | varios |
| `data/` secuencias NCF | **0** | tipos documento por país | DTE Chile |

---

## Módulos Enterprise — lista completa

Ver `evidence/odoo19-enterprise-modules.txt` (776 entradas).

Muestra (primeros 30):

```
account_3way_match, account_accountant, account_accountant_batch_payment,
account_accountant_check_printing, account_accountant_fleet, account_asset,
account_asset_fleet, account_avatax, account_bank_statement_extract,
account_bank_statement_import, account_batch_payment, account_budget, ...
```

---

## Módulos Community instalados vs disponibles

El inventario filesystem cubre **todos** los módulos oficiales. En `hellenia_dev` solo **108** están `installed`; los **1.347** restantes en BD están `uninstalled` pero **existen** en el tarball.

Para listar instalados:
```sql
SELECT name FROM ir_module_module WHERE state='installed' ORDER BY name;
```

---

## Conclusiones verificadas (con evidencia)

1. **Odoo 19 EE incluye exactamente 3 módulos RD:** `l10n_do`, `l10n_do_reports`, `l10n_do_check_printing`. No hay `l10n_do_edi`.

2. **`l10n_do` es localización contable básica** — plan de cuentas, impuestos, posiciones fiscales. El manifest admite que NCF requiere terceros o desarrollo.

3. **Framework LATAM documentos (`l10n_latam_invoice_document`) existe pero no está conectado a RD** — no es dependencia de `l10n_do` y está `uninstalled` en DEV.

4. **B01/B02/E31–E34 en escaneo global son falsos positivos para RD** — pertenecen a Colombia (`l10n_co_dian`), Mongolia, Uruguay, Bélgica POS, etc.

5. **606/607 en `l10n_do` son cuentas contables**, no libros DGII. `l10n_do_reports` no contiene reportes 606/607/608.

6. **Inventario completo reproducible** vía `scripts/generate-odoo19-module-inventory.py` + artefactos en `evidence/`.

---

## Referencias cruzadas

- Certificación fiscal Fase 5: `docs/DOMINICAN_FISCAL_CERTIFICATION.md`
- Brechas P0: `docs/GAP_ANALYSIS_RD.md` v3.0
- Resumen ejecutivo DAFC: `docs/PHASE5_EXECUTIVE_SUMMARY.md`

---

*Generado por escaneo automatizado de manifests Odoo 19.0-20260619. No asume capacidades no evidenciadas en código.*
