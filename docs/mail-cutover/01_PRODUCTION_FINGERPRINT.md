# 01 — Production Fingerprint

## Identidad

| Campo | Valor |
|---|---|
| Host | `justgroup` / `31.97.6.178` |
| Dominio | `justgroup.app` |
| Confirmación | **ESTE ES PRODUCCIÓN** |
| DB | `justech` (también existen `justech_20260708_ro`, `justech_pre_golive_ro` — no usados) |
| Servicio | `odoo` (active, systemd) |
| Conf | `/etc/odoo/odoo.conf` |
| addons_path | `/usr/lib/python3/dist-packages/odoo/addons`, `/usr/lib/odoo/enterprise`, `/usr/lib/odoo/custom-addons` |
| Usuario Linux | `odoo` |
| Odoo | ver `evidence/mail-cutover/prod/00_odoo_version.txt` |
| PostgreSQL | ver `evidence/mail-cutover/prod/00_pg_version.txt` |
| Git en servidor custom-addons | no es el repo de desarrollo; módulo desplegado en filesystem |

## Módulo policy (filesystem)

Path: `/usr/lib/odoo/custom-addons/justech_mail_outgoing_policy`

| Archivo | SHA256 (16) |
|---|---|
| `__manifest__.py` | `faf442ea56cb7f22` |
| `models/mail_mail.py` | `9449e4f76c58f63e` |
| `data/ir_config_parameter.xml` | `b68f5f965e59493c` |
| `models/__init__.py` | `86f0b884772309fd` |

**Models presentes:** solo `mail_mail.py`  
**Ausentes vs DEV P1:** `res_company.py`, `helpdesk_team.py`, `mail_compose_message.py`, `migrations/`, `tests/`

## DB module versions

Ver `evidence/mail-cutover/prod/01_modules.txt` — `justech_mail_outgoing_policy` **19.0.1.1.0** installed.

## Mail ICP (extracto)

- `justech_mail.outgoing_policy_enabled=True`
- `justech_mail.company_policies` = JUSTECH + Just Office (JSON parcial en evidencia)
- `mail.default.from=asistencia@justech.do`
- `mail.catchall.domain=justech.do`
