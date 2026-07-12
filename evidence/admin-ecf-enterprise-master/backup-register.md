# Backup master block — justech_dev

- Timestamp UTC: 2026-07-11T22:55:07Z
- Ruta servidor: `/opt/odoo-dev/backups/admin-ecf-master-20260711_225507`
- Dump: `justech_dev.dump` (75M) SHA256 `8b960320430212a37da5f8ecaed13717c39d0f6462427dbb751e7f0e5ae587f2`
- Filestore: `filestore.tgz` (365M) SHA256 `8ae844327130233fe44f8e7c4d322850a7cce4c45287d63fb8545b97c919e472`
- Restore test DB: `justech_lab_ecf_master` → COMPANIES=4 MOVES=2647 JUSTECH_INSTALLED=12 → DROP
- Resultado: RESTORE_OK
- Producción (justgroup.app): no tocada

## Continuación 2026-07-12

- Trabajo solo en erp.justech.do / justech_dev / `feature/fiscal-standard-consolidation`
- Backup master anterior sigue siendo el punto de rollback de BD
- Cierre técnico: ver `MASTER_BLOCK_STATUS.md` (PASS TÉCNICO / BLOQUEADO POR CERTIFICACIÓN DGII)
- Rollback: restaurar dump+filestore del backup `admin-ecf-master-20260711_225507`; revertir commit de la feature branch
