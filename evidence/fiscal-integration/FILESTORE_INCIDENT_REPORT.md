# Informe de incidente — Filestore erp.justech.do

| Campo | Valor |
|-------|-------|
| **Fecha incidente** | 2026-07-09 ~18:31 CEST (16:31 UTC) |
| **Entorno** | `erp.justech.do` / BD `justech_dev` |
| **Estado actual** | **RECUPERADO** (filestore restaurado 22:11 CEST) |
| **DEV-2** | **DETENIDO** |

---

## Resumen ejecutivo

El frontend de Odoo dejó de cargar CSS/JS porque **desapareció el filestore operativo de `justech_dev`**. No fue causado por XML/SCSS/manifest de `justech_l10n_do_reports`.

**Causa raíz confirmada:** script de restore del laboratorio NCF Phase 2 que **movió** (`mv`) el directorio `filestore/justech_dev` hacia `filestore/justech_ncf_lab` en lugar de **copiarlo**, dejando `justech_dev` sin archivos físicos.

---

## Síntomas

| Síntoma | Evidencia |
|---------|-----------|
| Página en blanco / sin CSS | Bundles `/web/assets/*` → HTTP 500 |
| Imágenes gigantes / layout roto | HTML sin JS/CSS |
| Assets corruptos aparentes | `FileNotFoundError` en `binary.py:150` |

---

## Timeline forense

| Hora (CEST +2) | Evento |
|----------------|--------|
| **18:24:02** | Backup `ncf-phase2-20260709_182401` — filestore **352 MB** íntegro |
| **18:25:19** | Script lab restore ejecutado — **`mv filestore/justech_dev → justech_ncf_lab`** |
| **18:31:38** | Primer `FileNotFoundError` en assets (`16:31:38 UTC` en log Odoo) |
| **18:37:31** | Odoo aún intenta leer archivos inexistentes en paths históricos |
| **21:44** | Backup DEV-1 captura filestore **451 bytes** (estado ya destruido) |
| **21:55** | Backup DEV-2 idem — **inválido para filestore** |
| **22:11** | Recovery: filestore restaurado desde backup ncf-phase2 pre-incidente |

---

## Causa raíz

### Script responsable

Ejecutado por agente Cursor en sesión NCF Phase 2 (`lab-restore-20260709_182519.log`):

```bash
rm -rf /opt/odoo-dev/data/filestore/${LAB_DB}
mkdir -p /opt/odoo-dev/data/filestore
tar xzf "$BACKUP/filestore_justech_dev.tar.gz" -C /opt/odoo-dev/data/filestore
mv /opt/odoo-dev/data/filestore/justech_dev /opt/odoo-dev/data/filestore/${LAB_DB}
```

### Por qué destruyó producción dev

1. El backup extrae el tarball como `filestore/justech_dev/`.
2. El script **mueve** ese directorio a `justech_ncf_lab`.
3. **`justech_dev` queda sin filestore** (o con restos mínimos al recrearse).
4. La BD `justech_dev` sigue activa con **4.272 `ir_attachment`** apuntando a paths inexistentes.
5. Odoo sirve HTML pero assets retornan 500 → UI rota.

### Evidencia del estado destruido

Snapshot forense pre-recovery (`RECOVERY-20260709_221056/filestore_broken_*.tar.gz`):

```
justech_dev/
justech_dev/checklist/57/5766ae337452e1f82a6344471ae273eefb124a84
justech_dev/57/5766ae337452e1f82a6344471ae273eefb124a84
```

Solo **1 archivo** + estructura `checklist/` residual (típico de GC parcial Odoo).

---

## Qué NO causó el incidente

| Descartado | Motivo |
|------------|--------|
| XML reports / manifest DEV-2 | Install posterior al wipe; sin ParseError |
| SCSS / JS / QWeb custom | Sin errores compilación |
| Cron | Sin jobs filestore configurados |
| Bash history root/odoo | Sin registros (history vacío o no persistente) |
| `rsync --delete` reports | Solo tocó addons, no filestore |

---

## Análisis solicitado (1–12)

| # | Área | Hallazgo |
|---|------|----------|
| 1 | `web.assets_backend` | Registros BD OK; archivos físicos ausentes |
| 2 | `web.assets_frontend` | Idem — HTTP 500 |
| 3 | Attachments assets | 149 URLs; `store_fname` sin archivo en disco |
| 4 | Último upgrade | DEV-2 reports ~20:04 UTC — **posterior** al incidente |
| 5 | Último módulo | `justech_l10n_do_reports` — no causante |
| 6 | Logs Odoo | `FileNotFoundError` masivo desde 16:31 UTC |
| 7 | Traceback | `ir_attachment._to_http_stream` → `os.stat` falla |
| 8 | JS errors | Consecuencia de bundles 500 |
| 9–12 | XML/SCSS/QWeb/manifest | Sin relación causal |

---

## Recovery aplicado

1. Stop `odoo-dev`
2. Snapshot filestore roto (forense)
3. Restore filestore desde `/opt/odoo-dev/backups/ncf-phase2-20260709_182401/filestore_justech_dev.tar.gz`
4. Start `odoo-dev`
5. BD **no restaurada** — histórico contable intacto

Post-recovery: assets HTTP **200**, login UI normal.

---

## Backups afectados

| Backup | Filestore | Estado |
|--------|-----------|--------|
| `ncf-phase2-20260709_182401` | 352 MB | ✅ **Válido** (pre-incidente) |
| `fiscal-integration-dev1-*` | 451 bytes | ❌ Inválido |
| `fiscal-integration-dev2-*` | 451 bytes | ❌ Inválido |

**Fallo del script de backup anterior:** `test -s` solo verificaba no-vacío, no tamaño mínimo ni integridad de assets.

---

## Medidas correctivas implementadas

### Script backup blindado (`fiscal-integration-dev1-backup.sh`)

1. **Falla si filestore vivo < 100 MB**
2. **Valida assets físicos** en `ir_attachment` (pre-backup)
3. **Valida `/web/assets` HTTP 200** en live (muestra 5 URLs)
4. **Valida login HTTP 200**
5. **Restore real** BD + filestore en temporal post-backup
6. **Valida assets físicos** post-restore
7. **Aborta todo** si cualquier check falla

### Procedimiento lab corregido (obligatorio)

```bash
# NUNCA mv justech_dev — siempre COPY:
rm -rf /opt/odoo-dev/data/filestore/justech_ncf_lab
mkdir -p /opt/odoo-dev/data/filestore/justech_ncf_lab
tar xzf "$BACKUP/filestore_justech_dev.tar.gz" -C /tmp
rsync -a /tmp/justech_dev/ /opt/odoo-dev/data/filestore/justech_ncf_lab/
rm -rf /tmp/justech_dev
chown -R odoo:odoo /opt/odoo-dev/data/filestore/justech_ncf_lab
```

---

## Riesgos residuales

| Riesgo | Mitigación |
|--------|------------|
| Backups DEV-1/DEV-2 inválidos | No usar para restore; nuevo backup blindado |
| Repetición mv en lab scripts | Prohibir `mv` cross-DB; solo `rsync/cp` |
| `data_dir` compartido dev+lab | Aislar paths; validar target antes de rm/mv |

---

## Restricciones respetadas post-incidente

- ❌ DEV-2 detenido
- ❌ Sin installs/upgrades
- ❌ Sin merge
- ❌ Sin tocar justgroup.app

---

## Próximo paso

1. Ejecutar **backup blindado** y archivar como baseline post-recovery
2. Decisión usuario: retomar DEV-2 o rollback controlado módulos fiscales
3. Auditar scripts en servidor que usen `mv` sobre filestore

---

## Referencias

- Log lab: `/opt/odoo-dev/evidence/ncf-phase2/lab-restore-20260709_182519.log`
- Recovery: `/opt/odoo-dev/evidence/fiscal-integration/RECOVERY-20260709_221056/`
- Backup válido: `/opt/odoo-dev/backups/ncf-phase2-20260709_182401/`
