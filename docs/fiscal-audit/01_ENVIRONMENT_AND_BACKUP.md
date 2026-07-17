# 01 — Entorno y backup (DEV)

## Confirmación expresa

**PRODUCCIÓN NO SERÁ MODIFICADA.**  
Host Prod identificado y excluido: `31.97.6.178` / BD `justech` / `justgroup.app` / servicio `odoo`.

## Entorno DEV (fuente: configuración instalada)

| Ítem | Valor evidenciado |
|---|---|
| Host | `207.244.242.58` |
| Hostname | `vmi3364393` |
| Dominio | `erp.justech.do` (HTTP 200) |
| BD activa | `justech_dev` (`db_name` en conf + conexiones PG) |
| Servicio | `odoo-dev.service` (`User=odoo`, `ExecStart=/usr/bin/odoo -c /opt/odoo-dev/conf/odoo-dev.conf`) |
| Conf | `/opt/odoo-dev/conf/odoo-dev.conf` |
| addons_path | `/usr/lib/python3/dist-packages/odoo/addons,/usr/lib/odoo/enterprise,/usr/lib/odoo/custom-addons,/opt/odoo-dev/custom-addons/justgroup/custom_addons` |
| data_dir / filestore | `/opt/odoo-dev/data` → `/opt/odoo-dev/data/filestore/justech_dev` (~471M) |
| Usuario Linux | `odoo` (uid 999) |
| Odoo | `19.0-20260324` |
| PostgreSQL | `16.14` |
| SMTP DEV | `odoo-dev-mail-sink.service` (neutralización) |

## Git

| Ubicación | Rama / commit |
|---|---|
| Servidor `/opt/odoo-dev/custom-addons/justgroup` | `development` @ `efda1ca71b6fef2505b7966290ddc6f304703304` (working tree sucio no fiscal) |
| Worktree local auditoría docs | `feature/ncf-range-status-alerts` @ tip documental |
| Baseline NCF | tag `ncf-alerts-baseline-v1` → `aaea7f5f4730a038f005a3e6010354f9da64963a` |

## Backup DEV

Ruta: `/opt/odoo-dev/backups/fiscal-master-audit-20260717_032503`

| Artefacto | Estado |
|---|---|
| `justech_dev.dump` (pg_dump -Fc) | OK (~51M) |
| `filestore_justech_dev.tar.gz` | OK (~345M) |
| Módulos `justech_l10n_do_*` + fiscal/e-CF | OK (`modules/*.tar.gz`) |
| Meta: conf, service, modules, pip | OK |

## Restore test

BD aislada `justech_dev_fiscal_audit_restore`:

| Check | Resultado |
|---|---|
| Rangos | 14/14 |
| AML | 9042/9042 |
| Partners | 1201 |
| Moves | 2410 |
| Attachments | 4375 |
| Sample move | `3787\|FP/2026/07/0003` |
| Sample partner | presente |
| Sample range | `1\|B01\|active` |
| PDF attachments | 608 |
| store_fname | 4075 |
| Filestore tar | OK |
| Login HTTP DEV | 200 |
| **Veredicto** | **PASS** |

Evidencia: `evidence/fiscal-audit/restore/result.txt`, `evidence/fiscal-audit/SQL/*`.
