# P0.1 — Matriz de propiedad / fuente de verdad NCF

| Concepto | Campo LATAM | Campo Justech | Modelo | Quién escribe | Quién valida | Quién muestra | Quién exporta | Fuente propuesta |
|---|---|---|---|---|---|---|---|---|
| Tipo documento (emisión) | `l10n_latam_document_type_id` | `justech_do_document_type_id` | `account.move` | Justech resolver/assignment | Motor Justech | UI Justech / FDP display | FDP prefix/name | **Justech** |
| Tipo documento (compra recibida) | `l10n_latam_document_type_id` | (opcional) | `account.move` | Usuario (UI LATAM) | Gate prefijo vs NCF | UI LATAM | FDP | **LATAM (entrada)** |
| Número NCF (emisión) | `l10n_latam_document_number` (mirror legacy) | `justech_do_ncf` | `account.move` | Assignment / manual Justech | Unicidad v2 + formato | FDP `get_ncf` | FDP | **Justech** |
| Número NCF (recibido) | `l10n_latam_document_number` | — | `account.move` | Usuario | Gate + duplicate | UI LATAM / FDP | FDP | **LATAM** |
| Prefijo | `doc_code_prefix` | `justech.do.fiscal.document.type.prefix` | types | vía tipo | `check_type_ncf_prefix_consistency` | FDP | FDP | Derivado del tipo canónico del flujo |
| Secuencia / rango | Adel `account.fiscal.sequence` (congelado) | `justech.do.ncf.range` | range | `consume_next` | estado/cupo | Range UI | N/A | **Justech** |
| Compañía | `company_id` | igual | move/range | Odoo | rules | — | report.company_id | estándar |
| Diario | journal + Adel latam flag off | `justech_do_use_ncf` | journal | adel_freeze fuerza off | — | — | — | Justech emission flag |
| Tipo ingreso 607 | `l10n_do_income_type` | `justech_do_income_type_607` | move | compute/user | soft | FDP | 607 exporter | **Justech → Adel fallback** |
| Tipo gasto 606 | `l10n_do_expense_type` | `justech_do_expense_type_id` | move | user + mirror code | required on post | UI | FDP | **Justech** (+ mirror código Adel OK) |
| Doc fiscal contacto | `l10n_do_dgii_tax_payer_type` | `justech_do_default_document_type_id` | partner | partner/padron | constraints | partner form | id type | **Justech defaults** |
| NCF modificado / origen | `l10n_do_origin_ncf` | `justech_do_origin_ncf` / `_ncf_modified` | move | NC/ND assignment | — | FDP | 606/607 col F | **Justech → Adel fallback** |
| Anulación | `l10n_do_cancellation_type` | void fields Justech | move | void wizard | fiscal manager | admin | 608 FDP | **Justech** |
| Forma de pago | — | — | — | inferido export | export | review | 606/607 | Inferencia export (sin dual store) |
| Retenciones | — | payments_withholding | payment | wizard | — | — | 623 | Justech payments |
| e-CF | LATAM E* types | FDP `is_ecf` | move | recibido hoy | format | — | reports | Recibido LATAM; emisión e-CF futura Justech |

## Notas de ejecución

- Create/write/onchange: modo compra `received` limpia Justech NCF; `issued` usa Justech.
- Post: expense → validate received → assign Justech → super; Adel `get_fiscal_number` bloqueado.
- Dual-write (`ncf_dual_write`): **OFF** tras P0.1 — solo Justech en emisión.
- FDP: **solo lectura**, prioridad Justech → LATAM → estándar.
