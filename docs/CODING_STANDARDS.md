# Estándares de codificación — Hellenia Odoo

**Obligatorio** para todo desarrollo custom en `custom/`.

---

## Reglas absolutas

| # | Regla |
|---|-------|
| 1 | **Nunca** modificar código en `enterprise/` |
| 2 | **Nunca** modificar código Community (imagen Docker) |
| 3 | **Siempre** personalizar mediante `_inherit` en módulos `custom/` |
| 4 | **Nunca** copiar archivos Enterprise/Community a `custom/` |
| 5 | **Solo** módulos oficiales Odoo como dependencias, salvo aprobación |

---

## Python — PEP 8

| Aspecto | Estándar |
|---------|----------|
| Indentación | 4 espacios |
| Longitud línea | 88–100 caracteres (Ruff/black) |
| Imports | stdlib → third-party → odoo → local |
| Nombres | `snake_case` funciones/variables; `PascalCase` modelos |
| Docstrings | Google style en métodos públicos no triviales |

### Ejemplo modelo

```python
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    hellenia_customer_tier = fields.Selection(
        selection=[
            ("retail", "Retail"),
            ("corporate", "Corporate"),
        ],
        string="Customer Tier",
    )
```

---

## Convenciones Odoo oficiales

### Manifest (`__manifest__.py`)

- Versión: `19.0.X.Y.Z` (X.Y.Z = semver del módulo)
- `depends`: solo lo necesario; orden irrelevante
- `data/`: orden importa — security antes de views que referencien grupos
- `license`: `LGPL-3` para módulos Hellenia salvo decisión contraria

### XML IDs

- Prefijo: `hellenia_<modulo>_` o `justech_<modulo>_`
- Ejemplo: `hellenia_inventory_view_picking_form_inherit`

### Seguridad

- Todo modelo nuevo: entrada en `security/ir.model.access.csv`
- Grupos custom: `security/<modulo>_security.xml` antes de views

### Hooks oficiales

| Hook | Uso |
|------|-----|
| `pre_init_hook` | Validaciones pre-instalación |
| `post_init_hook` | Datos one-shot post-instalación |
| `uninstall_hook` | Limpieza al desinstalar |
| `@api.model_create_multi` | Preferir sobre `create` override |
| `@api.constrains` | Validaciones de negocio |
| `@api.depends` | Campos computados |

### Herencia

| Tipo | Cuándo |
|------|--------|
| `_inherit = "model.name"` | Extender modelo existente |
| `_inherit = ["a", "b"]` | Mixin múltiple (raro) |
| `_name = "new.model"` + `_inherit = "mail.thread"` | Modelo nuevo con mixins |

**Prohibido:** `patch` de archivos, monkey-patching, override sin `super()`.

---

## JavaScript / OWL (si aplica)

- Seguir estructura Odoo 19 (`@odoo-module`)
- Assets en `static/src/` declarados en `__manifest__.py` → `assets`
- No modificar assets Enterprise

---

## SQL

- Evitar SQL crudo; usar ORM
- Si es inevitable: parametrizado, sin concatenación de strings
- Nunca en controllers sin permisos explícitos

---

## Commits Git

Formato recomendado:

```
tipo(modulo): descripción breve

feat(hellenia_inventory): add barcode validation on picking
fix(hellenia_account): correct ITBIS computation on credit notes
docs(hellenia_base): update README dependencies
chore(scripts): fix backup retention symlinks
```

Tipos: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`

---

## Revisión de código (checklist)

- [ ] Solo archivos en `custom/`
- [ ] `_inherit` correcto, sin copiar código Odoo
- [ ] Security CSV/XML completo
- [ ] Tests en `tests/` para lógica no trivial
- [ ] Traducciones en `i18n/es.po` si hay strings user-facing
- [ ] `__manifest__.py` version bump si cambio funcional
- [ ] Sin secretos ni URLs internas hardcodeadas

---

## Referencias Odoo oficiales

- [Coding guidelines](https://www.odoo.com/documentation/19.0/contributing/development/coding_guidelines.html)
- [Git guidelines](https://www.odoo.com/documentation/19.0/contributing/development/git_guidelines.html)

---

## Referencias internas

- [CUSTOM_MODULE_GUIDE.md](CUSTOM_MODULE_GUIDE.md)
- [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)
