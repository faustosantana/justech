# 04 — Auditoría de código (sin modificar)

## Alcance revisado

`justech_l10n_do_base`, `justech_l10n_do_ncf`, `justech_l10n_do_reports` (+ interferencias: adel_freeze, payments_withholding, ecf, hellenia_account).

## Hallazgos de código (evidencia)

| ID | Tema | Evidencia | Severidad |
|---|---|---|---|
| FISC-AUD-010 | `env.cr.commit()` en import padrón | `rnc_padron_import_service.py` (múltiples líneas) | ALTO |
| FISC-AUD-011 | `except Exception` amplio | FDP, diagnostic, ncf_range chatter, account_move sync | MEDIO |
| FISC-AUD-012 | `sudo()` frecuente (69 hits núcleo) | base/ncf/reports | MEDIO — requiere revisión caso a caso |
| FISC-AUD-013 | `search(..., limit=1)` en centros | `fiscal_range_center.py`, latam type | MEDIO |
| FISC-AUD-014 | Dual resolución NCF (FDP) | `fiscal_data_provider.py` | ALTO (diseño) |
| — | Overrides account.move con `super()` | `ncf/models/account_move.py` create/write/_post/action_post | OK (no hallazgo) |
| — | TODO/FIXME en núcleo | 0 | OK |
| — | Baseline alertas | `ncf_range.py` PROTECTED | **NO TOCAR** |

## account.move (ncf)

- `create` / `write` / `_post` / `action_post` / `button_draft` / constraints unicidad / `init` indexes.
- Mezcla presentación (vistas) vs validación en modelo: validaciones de publicación presentes; UI no es única barrera.

## res.partner

- Constraints RNC; create/write con detección duplicados RNC/cédula.

## Riesgos de compatibilidad Odoo 19

- `ir_cron` sin `model_id` directo (vía `ir_actions_server_id`) — scripts de auditoría deben adaptarse.
- `mail.activity` sin columna `state` (usa `date_done`).

## Código muerto / legacy

- Posible coexistencia `hellenia_account` withholding vs `justech_l10n_do_payments_withholding` (interferencia potencial — confirmar en remediación).
- Campos Adel (`l10n_do_*`) + Justech (`justech_do_*`) + LATAM en el mismo move.
