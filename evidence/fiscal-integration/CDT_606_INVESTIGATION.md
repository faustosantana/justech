# Investigación — Impuesto «2% CDT» en formato 606

| Campo | Valor |
|-------|-------|
| **Fecha** | 2026-07-09 |
| **Entorno** | `erp.justech.do` / `justech_dev` (solo lectura) |
| **Período** | 202606 |
| **Alcance** | 5 facturas incompletas post-FDP |

---

## 1. Facturas afectadas

| Factura | ID | Proveedor | NCF | Base | Total | CDT |
|---------|-----|-----------|-----|------|-------|-----|
| FP/2026/06/0083 | 3537 | Dominet S.R.L. | E310000000209 | 7,254.20 | 9,430.46 | **145.08** |
| FP/2026/06/0084 | 3538 | Columbus Networks Dominicana SA | E310000019120 | 125.00 | 162.50 | **0.04** |
| FP/2026/06/0044 | 3432 | Compañía Dominicana de Teléfonos S.A. | E310015894257 | 1,042.31 | 1,355.01 | **20.85** |
| FP/2026/06/0045 | 3433 | Compañía Dominicana de Teléfonos S.A. | E310015890327 | 435.75 | 566.49 | **8.72** |
| FP/2026/06/0046 | 3435 | Compañía Dominicana de Teléfonos S.A. | E310015893083 | 1,387.88 | 1,804.25 | **27.76** |

**Patrón común:** las 5 son facturas de **telecomunicaciones** con la misma estructura de impuestos en líneas:

| Impuesto | `account.tax` id | Tasa | Grupo fiscal | Rol |
|----------|------------------|------|--------------|-----|
| 18% ITBIS | 5 | 18% | ITBIS | Impuesto transferido |
| 10% ISC | 14 | 10% | ISC | Impuesto selectivo al consumo |
| **2% CDT** | **15** | **2%** | **Other Taxes** | Contribución telecomunicaciones |

Ejemplo **FP/2026/06/0084** (líneas contables):

| Línea | Tipo | Monto |
|-------|------|------:|
| comunicacion | producto | 125.00 |
| 18% ITBIS | impuesto | 0.38 |
| 10% ISC | impuesto | 0.21 |
| **2% CDT** | impuesto | **0.04** |

**Alcance en junio/2026:** solo **5 de 90** facturas del 606 tienen CDT (`tax_line_id=15`). No hay otras facturas con ISC sin CDT en el período.

---

## 2. ¿Qué es exactamente «2% CDT»?

| Pregunta | Respuesta |
|----------|-----------|
| ¿Es impuesto? | **Sí** — `account.tax`, `type_tax_use=purchase`, `amount_type=percent` |
| ¿Es retención? | **No** — balance positivo en línea de impuesto (cargo, no retención negativa) |
| ¿Es ISC? | **No** — ISC es impuesto aparte (10%, tax id 14, grupo ISC) |
| ¿Es cargo manual? | **No** — viene del catálogo estándar Odoo RD |
| ¿Origen en sistema? | XML-ID `account.1_tax_2_telco` (localización `account` / plan DO) |

**Definición fiscal:** **CDT** = *Contribución al Desarrollo de las Telecomunicaciones*, gravamen del **2%** sobre servicios de telecomunicaciones en RD. Es un impuesto/tasa adicional que forma parte del valor del comprobante fiscal de compra.

---

## 3. Clasificación DGII / 606

Según instructivo oficial DGII (Formato 606, NG-07-2018):

| Columna Excel | Campo DGII | Uso para estas facturas |
|---------------|------------|-------------------------|
| **N** | ITBIS Facturado | Monto línea 18% ITBIS |
| **W** | Impuesto Selectivo al Consumo | Monto línea 10% ISC |
| **X** | **Otros Impuestos/Tasas** | **Monto línea 2% CDT** |

La DGII indica explícitamente que impuestos como **CDT** (telecomunicaciones) van en **«Otros Impuestos/Tasas»** (casilla 21 / columna X), no en ITBIS ni ISC.

Mapeo Justech (`dgii_606_mapping.json`):

- Columna **W** → `justech_do_isc_amount` (campo marcado *faltante*)
- Columna **X** → «Otros Impuesto/Tasas» — notas: *otros impuestos no ITBIS/ISR*

---

## 4. Diagnóstico de causa

| Hipótesis | ¿Aplica? | Evidencia |
|-----------|----------|-----------|
| Configuración incorrecta del impuesto en Odoo | **No** | Tax estándar `account.1_tax_2_telco`, grupo «Other Taxes», usado correctamente en facturas telecom |
| Mapeo DGII faltante en catálogo retenciones | **No** | CDT no es retención; `hellenia.withholding.catalog` no está instalado y no aplica |
| Error de registro / datos en factura | **No** | Líneas ITBIS + ISC + CDT coherentes; asientos posted correctos |
| **Gap del módulo `justech_l10n_do_reports`** | **Sí** | Ver abajo |

### Gap en código (causa raíz)

**Validación** (`dgii_606_exporter._dgii_validate_single_move`):

```python
# Solo acepta ITBIS o nombre con "ISC"
unknown = positive_taxes.filtered(
    lambda l: not self._dgii_is_itbis_tax(l.tax_line_id)
    and "ISC" not in (l.tax_line_id.name or "").upper()
    ...
)
```

→ **CDT no está en la lista blanca** → error «impuesto no clasificado para DGII: 2% CDT».

**Exportación** (`_dgii_build_row_values`):

```python
"W": 0.0,   # ISC — siempre cero (no implementado)
"X": 0.0,   # Otros impuestos — siempre cero (no implementado)
```

→ Aunque se silenciara la validación, el Excel 606 **no reportaría** ISC ni CDT a DGII.

**Conclusión:** es un **error de módulo** (clasificación y exportación incompletas), **no** un error de datos ni de configuración contable.

---

## 5. Impacto

| Área | Impacto |
|------|---------|
| Contabilidad / asientos | **Ninguno** — correctos |
| Facturas / histórico | **Ninguno** |
| 606 validación | **5 facturas** marcadas incompletas (de 90) |
| 606 exportación DGII | ITBIS en col. N sí; **ISC (W) y CDT (X) en cero** para todas las telecom |
| Riesgo DGII | Archivo 606 incompleto vs valor real del NCF si se enviara sin col. W/X |
| Otros períodos | Cualquier compra telecom con `account.1_tax_2_telco` tendrá el mismo comportamiento |

---

## 6. Propuesta segura de corrección

### Recomendación: **cambio de código** en `justech_l10n_do_reports` (sin tocar facturas ni impuestos)

#### Fase A — Clasificación fiscal de impuestos (606)

Añadir en exportador 606 (o helper compartido):

| Tipo | Criterio | Columna 606 |
|------|----------|-------------|
| ITBIS | Existente (`_dgii_is_itbis_tax`) | N |
| ISC | Nombre contiene `ISC` o grupo tax ISC | W |
| CDT / Otros | Nombre contiene `CDT`, o xmlid `account.1_tax_2_telco`, o grupo «Other Taxes» en compras telecom | X |
| Retenciones | Existente (`_withholding_breakdown`, amount < 0) | O, U |

#### Fase B — Validación

- Dejar de marcar error en impuestos positivos ya clasificados (ITBIS, ISC, CDT/otros).
- Mantener error solo para impuestos **realmente desconocidos**.

#### Fase C — Exportación

- Calcular sumas por tipo desde `move.line_ids` (`tax_line_id`).
- Poblar **W** = ISC, **X** = CDT + otros impuestos no ITBIS/ISC.

#### Fase D — Pruebas

- Test unitario con factura telecom (ITBIS + ISC + CDT).
- Re-validar 606/202606 en `justech_dev`: expectativa **0 errores «sin NCF»**, **0 errores CDT**, 5 facturas pasan a válidas (salvo otros problemas).
- Verificar fila E310000019120: N=0.38, W=0.21, X=0.04.

### Lo que **no** se recomienda

| Acción | Por qué no |
|--------|------------|
| Renombrar impuesto CDT a «ISC» | Falsifica clasificación DGII |
| Mapear CDT en `hellenia.withholding.catalog` | No es retención |
| Modificar facturas posted | Prohibido / innecesario |
| Excluir facturas telecom del 606 | Pérdida de reporte fiscal |

### Alternativa mínima (solo validación)

Reconocer `CDT` en validación sin exportar W/X → las 5 facturas pasarían a «válidas» pero el **archivo DGII seguiría incompleto**. **No recomendado** como solución final.

---

## 7. Resumen ejecutivo

| Ítem | Valor |
|------|-------|
| **Causa** | Gap en `justech_l10n_do_reports`: validador no reconoce CDT; exportador no llena columnas W/X |
| **Naturaleza CDT** | Impuesto de compra 2% telecom (no retención, no ISC) |
| **Clasificación DGII** | Columna **X** — Otros Impuestos/Tasas |
| **¿Error de datos?** | No |
| **¿Error de configuración impuesto?** | No (tax estándar Odoo RD) |
| **¿Requiere cambio de código?** | **Sí** (recomendado) |
| **¿Requiere cambio de configuración?** | **No** |
| **Riesgo de la corrección** | Bajo — solo lectura de líneas existentes; sin migración ni backfill |

---

## 8. Evidencia consultada

- SQL read-only `justech_dev` (facturas, `account_tax` 5/14/15, líneas)
- `custom/justech_l10n_do_reports/models/dgii_606_exporter.py`
- `custom/justech_l10n_do_reports/data/dgii_606_mapping.json`
- Instructivo DGII Formato 606 (casillas 20 ITBIS selectivo / 21 Otros impuestos)
- `evidence/fiscal-integration/FDP-deploy-20260709/606_compare_202606.json`
