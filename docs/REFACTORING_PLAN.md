# Plan de Refactorización — Justech l10n DO

**Fecha:** 2026-06-30  
**Principio:** Sin nuevas funcionalidades — solo hardening y productización  
**Restricción:** No tocar TEST/PROD; cambios en rama dedicada `feature/justech-l10n-do-hardening`

---

## Sprint 0 — P0 Hardening (obligatorio antes de TEST)

### REF-001: Record rules multi-empresa

**Archivo nuevo:** `security/justech_l10n_do_rules.xml` (en cada módulo o base compartido)

```xml
<record id="rule_ncf_range_company" model="ir.rule">
    <field name="name">NCF Range: multi-company</field>
    <field name="model_id" ref="model_justech_do_ncf_range"/>
    <field name="domain_force">[('company_id', 'in', company_ids)]</field>
</record>
```

Replicar para: `fiscal.document.type`, `ncf.consumption`, `fiscal.report`, `fiscal.report.line`.

**Tests:** `test_record_rules_company_isolation`

---

### REF-002: Lock concurrencia NCF

**Archivo:** `ncf_range.py` → `consume_next`

```python
def consume_next(self, move):
    self.ensure_one()
    self.env.cr.execute(
        "SELECT id FROM justech_do_ncf_range WHERE id = %s FOR UPDATE",
        [self.id],
    )
    self.invalidate_recordset()
    ...
```

**Tests:** `test_concurrent_consume_unique_ncf` (2 workers o sequential simulate)

---

### REF-003: Seguridad `action_void_ncf`

**Archivo:** `account_move.py`

```python
def action_void_ncf(self):
    if not self.env.user.has_group(
        "justech_l10n_do_base.group_justech_do_fiscal_manager"
    ):
        raise AccessError(_("Only fiscal managers can void NCF."))
    ...
```

Añadir `void_reason` required si `justech_do_ncf_voided` transition.

---

### REF-004: Constraint SQL NCF único

```python
# account.move — migración
_models.Constraint(
    'unique(company_id, justech_do_ncf)',
    'NCF must be unique per company.',
    # condición: solo posted non-voided — evaluar partial index PostgreSQL
)
```

---

## Sprint 1 — P1 Calidad código

### REF-005: Migrar `_sql_constraints` → `models.Constraint`

Afecta: `fiscal_document_type.py`, `ncf_range.py`

### REF-006: Extraer mixin fiscal

**Archivo nuevo:** `justech_l10n_do_base/models/fiscal_mixin.py`

- `_validate_ncf_format(ncf)`
- `_normalize_rnc(vat)`

Mover desde `ncf_range` y `res_partner`.

### REF-007: Configurable document type resolution

Reemplazar `env.ref("doc_type_b01")` por:

```python
journal.justech_do_document_type_ids.filtered(
    lambda d: d.move_type == self.move_type and d._matches_partner(self.partner_id)
)
```

Requiere método `_matches_partner` en document type.

### REF-008: ITBIS helper en reports

```python
def _get_move_itbis(self, move):
    return abs(sum(
        move.line_ids.filtered(
            lambda l: l.tax_line_id and l.tax_line_id.l10n_do_itbis
        ).mapped("balance")
    ))
```

Requiere campo/tag en impuesto o búsqueda por `tax_group_id` RD.

---

## Sprint 2 — P1 Productización

### REF-009: i18n

- Generar `i18n/es_DO.po` para los 3 módulos
- Envolver strings en `res_partner`, `fiscal_document_type`

### REF-010: Branding neutro

- Manifests: `website` → Justech
- README: eliminar "Hellenia" como cliente único

### REF-011: Tests adicionales

| Test | Prioridad |
|------|-----------|
| B03 debit note | P1 |
| B13 purchase unit | P1 |
| Report 606 | P1 |
| export CSV | P2 |
| fiscal disabled | P2 |

---

## Sprint 3 — P2 Mejoras estructurales

### REF-012: `mail.thread` en rangos

```python
_inherit = ["mail.thread", "mail.activity.mixin"]
```

### REF-013: Cron expiración rangos

```python
@api.model
def _cron_expire_ranges(self):
    today = fields.Date.today()
    self.search([
        ("state", "=", "active"),
        ("date_to", "<", today),
    ]).write({"state": "expired"})
```

Implementar uso de `justech_do_ncf_alert_days`.

### REF-014: Tests common mixin

`tests/common.py` con `JustechDoTestMixin` para setup compartido.

---

## Orden de ejecución

```
Sprint 0 (P0) ──► Validar en DEV ──► Gate TEST
     │
Sprint 1 (P1 code) ──► CI tests
     │
Sprint 2 (product) ──► Beta 2da empresa
     │
Sprint 3 (P2) ──► GA preparation
```

---

## Criterios de aceptación refactor

- [ ] `PHASE6_MVP ok: true` sigue PASS post cada sprint
- [ ] 0 regresiones contables (balanced entry test)
- [ ] Nuevos tests P0 en CI
- [ ] Sin cambio comportamiento fiscal visible para usuario (salvo fixes seguridad)

---

## Qué NO refactorizar ahora

- Formato TXT DGII (nueva funcionalidad — fase DGII)
- eNCF / POS / Infile
- Reescritura completa de reportes a SQL
- Migración a OWL components custom
