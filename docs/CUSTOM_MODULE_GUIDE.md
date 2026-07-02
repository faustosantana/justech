# Guía de módulos custom — Hellenia Odoo

**Ubicación única:** `custom/`  
**Estado actual:** Esqueletos — **no instalar ni desarrollar** hasta completar las [cuatro comprobaciones](PROJECT_STRATEGY.md#política-de-módulos-custom-justech)

---

## Política Justech (obligatoria antes de custom)

| # | Comprobación |
|---|--------------|
| 1 | La funcionalidad **no existe** en el producto desplegado |
| 2 | **No existe** configuración oficial |
| 3 | **No existe** módulo oficial Odoo |
| 4 | **No existe** workaround oficial documentado |

Documentar evidencia en [GAP_ANALYSIS_RD.md](GAP_ANALYSIS_RD.md). **No modificar core.** **No módulos terceros.**

---

## Módulos del proyecto

| Módulo | Propósito | Depende de |
|--------|-----------|------------|
| `justech_core` | Utilidades compartidas Justech | `base` |
| `hellenia_base` | Configuración base Hellenia | `base` |
| `hellenia_inventory` | Extensiones inventario | `hellenia_base`, `stock` |
| `hellenia_account` | Extensiones contabilidad | `hellenia_base`, `account` |
| `hellenia_reports` | Reportes propios | `hellenia_base` |
| `hellenia_pos` | Punto de venta | `hellenia_base`, `point_of_sale` |

Cada módulo es un **proyecto independiente** con README propio.

---

## Estructura estándar (obligatoria)

```
custom/<modulo>/
├── README.md                 # Documentación del módulo
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   └── <modelo>.py           # Cuando haya lógica
├── views/
│   └── <modulo>_views.xml
├── security/
│   └── ir.model.access.csv
├── data/
│   └── <datos>.xml           # Datos del módulo (no globales)
├── static/
│   └── description/
│       └── icon.png          # Opcional
├── tests/
│   ├── __init__.py
│   └── test_<modulo>.py
└── i18n/
    └── es.po
```

### Directorio `data/` global vs módulo

| Ubicación | Cuándo usar |
|-----------|-------------|
| `data/` (raíz proyecto) | Datos transversales no acoplados a un módulo |
| `custom/<modulo>/data/` | Datos que se cargan al instalar el módulo |

---

## Crear un módulo nuevo

1. Copiar estructura de `hellenia_base/` como plantilla
2. Renombrar y ajustar `__manifest__.py`
3. Agregar dependencias mínimas
4. Documentar en README.md del módulo
5. PR a `hellenia-odoo-infra`

**Prefijos permitidos:** `hellenia_`, `justech_`

---

## Orden de instalación recomendado (futuro)

```
1. justech_core          (opcional si hellenia_base no lo requiere aún)
2. hellenia_base
3. hellenia_inventory | hellenia_account | hellenia_reports | hellenia_pos
```

Los esqueletos actuales **no deben instalarse** — `test_module_installable` fallará si se instalan sin estar listos.

---

## Desarrollo de un modelo nuevo

### 1. Modelo

```python
# custom/hellenia_inventory/models/stock_picking.py
from odoo import fields, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    hellenia_delivery_notes = fields.Text(string="Delivery Notes")
```

### 2. Registrar en models/__init__.py

```python
from . import stock_picking
```

### 3. Vista

```xml
<!-- custom/hellenia_inventory/views/stock_picking_views.xml -->
<odoo>
  <record id="view_picking_form_hellenia" model="ir.ui.view">
    <field name="name">stock.picking.form.hellenia</field>
    <field name="model">stock.picking</field>
    <field name="inherit_id" ref="stock.view_picking_form"/>
    <field name="arch" type="xml">
      <field name="origin" position="after">
        <field name="hellenia_delivery_notes"/>
      </field>
    </field>
  </record>
</odoo>
```

### 4. Manifest

```python
"data": [
    "security/ir.model.access.csv",
    "views/stock_picking_views.xml",
],
```

### 5. Test

```python
from odoo.tests import TransactionCase

class TestHelleniaInventory(TransactionCase):
    def test_picking_has_delivery_notes(self):
        picking = self.env["stock.picking"].create({...})
        self.assertFalse(picking.hellenia_delivery_notes)
```

### 6. Desplegar

```bash
scripts/deploy-dev.sh
scripts/update-custom-modules.sh dev hellenia_inventory
```

---

## Traducciones

- Strings user-facing: envolver en `_()` en Python, `string=` en fields
- Exportar: `odoo-bin ... --i18n-export` (futuro script)
- Archivo: `i18n/es.po` (español República Dominicana)

---

## Qué no hacer

| Acción | Alternativa |
|--------|-------------|
| Editar `enterprise/l10n_do_edi/` | `_inherit` en `hellenia_account` |
| Copiar vista Enterprise | `inherit_id` + xpath |
| Módulo OCA sin aprobación | Proponer en PR con justificación |
| Lógica en `data/` raíz | Módulo con manifest |

---

## Referencias

- [CODING_STANDARDS.md](CODING_STANDARDS.md)
- [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
