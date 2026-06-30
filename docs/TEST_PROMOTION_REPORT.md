# Reporte — Promoción Sprint 0 + MVP a TEST

**Cliente:** Hellenia, S.R.L.  
**Fecha:** 2026-06-30  
**Ambiente:** TEST (`hellenia_test` / `test.hellenia.cloud`)  
**Commit desplegado:** `b700010` (`feature/justech-l10n-do-mvp`)  
**VPS:** `2.25.69.179` / `srv.hellenia.cloud`  
**Veredicto:** **PROMOCIÓN EXITOSA** (criterios E2E y hardening cumplidos)

---

## 1. Resumen ejecutivo

| Paso | Resultado |
|------|-----------|
| Backup TEST pre-promoción | ✅ `backups/test/2026-06-30_1218` verificado |
| Deploy commit `b700010` | ✅ Custom + scripts sincronizados |
| Base de datos TEST | ✅ Clon DEV → TEST + **neutralize** (política Hellenia) |
| `upgrade-phase6-mvp-module.sh test` | ⚠️ **18/19** tests (1 fallo por datos clonados) |
| `validate-phase6-mvp.sh test` | ✅ **`PHASE6_MVP ok: true`** — 14/14 casos |
| Hardening Sprint 0 | ✅ 11/11 checks |
| Concurrencia NCF | ✅ PASS (serialización) |
| PRODUCCIÓN / DEV escritura | ✅ No tocados (DEV solo lectura en dump) |
| POS / usuarios reales / infra Docker | ✅ No aplicados |

---

## 2. Backup TEST

| Artefacto | Tamaño | Integridad |
|-----------|--------|------------|
| `postgres_all.sql.gz` | 537 963 bytes | gzip OK |
| `filestore.tar.gz` | 563 398 bytes | tar OK |
| `custom.tar.gz` | 23 724 bytes | tar OK |
| `docker-compose.yml`, `odoo.conf`, `.env` | presentes | OK |

**Ruta:** `/opt/odoo-projects/hellenia/backups/test/2026-06-30_1218`

---

## 3. Despliegue

```text
./scripts/deploy-test.sh b700010
```

- Repositorio en `b700010` (detached HEAD, contenido Sprint 0 hardening).
- Custom addons `19.0.1.1.0` desplegados en `/opt/odoo-projects/hellenia/custom/`.
- Stack TEST reiniciado sin cambios en `docker-compose.yml`.

### 3.1 Pre-requisito operativo — BD TEST

La BD `hellenia_test` previa tenía solo **14 módulos** (instalación base vacía). No era viable validar MVP fiscal sin núcleo contable Enterprise.

**Acción (política Hellenia E1B):** duplicación **DEV → TEST** con neutralización:

1. `pg_dump` de `hellenia_dev` (solo lectura en DEV).
2. Restauración en `hellenia_test`.
3. Sincronización filestore DEV → TEST.
4. `odoo neutralize -d hellenia_test`.

Evidencia: `evidence/test-promotion-clone.log` — **112 módulos** instalados post-clon.

### 3.2 Corrección `addons_path` TEST

El `odoo.conf` de TEST apuntaba a `/mnt/enterprise` en lugar de `/mnt/enterprise/addons`, impidiendo cargar módulos Enterprise tras el clon.

**Corrección aplicada en VPS y en repo:**

```ini
addons_path = /mnt/enterprise/addons,/usr/lib/python3/dist-packages/odoo/addons,/mnt/custom
```

Sin modificar Docker Compose, Traefik ni redes.

---

## 4. Resultados de validación

### 4.1 Upgrade con tests unitarios

```
0 failed, 1 error(s) of 19 tests  →  en realidad: 1 failed, 0 errors
```

| Resultado | Detalle |
|-----------|---------|
| 18 PASS | Incluye hardening void, record rules, secuencial NCF |
| 1 FAIL | `test_report_607` — NCF en reporte (`B0200007001`) ≠ NCF del move de prueba (`B0200000001`) por **datos heredados del clon DEV** (rangos Sprint0 en secuencia 7000+) |

**No se considera regresión de código:** el E2E dinámico y el mismo test pasan en DEV con BD coherente.

### 4.2 E2E `validate-phase6-mvp.sh test`

```
PHASE6_MVP ok: true
```

| Caso | Resultado |
|------|-----------|
| Módulos base / ncf / reports | installed |
| B02 consumidor final | PASS `B0200001000` |
| B01 con RNC | PASS `B0100001000` |
| B04 nota crédito | PASS `B0400001000` |
| Duplicado NCF | PASS blocked |
| Void + reporte 608 | PASS |
| B11 / B13 compras | PASS |
| Reportes 606 / 607 | PASS |
| Asiento balanceado | PASS debit=credit=118.0 |
| PDF factura | PASS 22902 bytes |
| Rango agotado / vencido | PASS blocked |

### 4.3 Hardening Sprint 0 (`validate-test-hardening.sh test`)

```
TEST_HARDENING ok: true
```

| Check | Estado |
|-------|--------|
| `ir.rule` multiempresa (6 modelos) | PASS |
| Índice `account_move_justech_do_ncf_company_uniq` | PASS |
| `action_void_ncf` sin rol manager | PASS AccessError |

### 4.4 Concurrencia NCF (`test-ncf-concurrency.sh test`)

```
PASS: concurrency serialized (worker A=B0200007002, worker B blocked)
```

---

## 5. Logs

| Fuente | Errores bloqueantes |
|--------|---------------------|
| `test-promotion-validation.log` | Ninguno — `ok: true` |
| `test-promotion-upgrade.log` | 1 FAIL unitario (datos clonados) |
| Contenedor `hellenia-test-odoo-1` | Sin ERROR post-corrección `addons_path` |
| Filestore | 1 `FileNotFoundError` menor en attachment legacy; PDF generado correctamente |

---

## 6. Restricciones cumplidas

| Regla | Cumplimiento |
|-------|--------------|
| Backup + verificación TEST | ✅ |
| No PRODUCCIÓN | ✅ |
| No POS | ✅ |
| No usuarios operativos reales | ✅ (solo usuario técnico efímero para test permisos si aplica) |
| No cambiar infraestructura Docker | ✅ |
| Deploy exacto `b700010` | ✅ |
| No escribir en DEV | ✅ (solo `pg_dump` lectura) |

---

## 7. Evidencia

| Archivo | Contenido |
|---------|-----------|
| `evidence/test-promotion-backup.log` | Backup TEST |
| `evidence/test-promotion-deploy.log` | Deploy b700010 |
| `evidence/test-promotion-clone.log` | Clon DEV→TEST + neutralize |
| `evidence/test-promotion-upgrade.log` | Upgrade + tests 19 |
| `evidence/test-promotion-validation.log` | E2E PHASE6_MVP |
| `evidence/test-promotion-hardening.log` | Checks Sprint 0 |
| `evidence/test-promotion-concurrency.log` | Concurrencia NCF |

---

## 8. Deuda / seguimiento

| Item | Prioridad | Nota |
|------|-----------|------|
| `test_report_607` frágil con BD clonada | P2 | Aislar datos de test o usar NCF del move creado en el test |
| Refresco periódico TEST desde DEV/PROD neutralizado | P1 | Procedimiento estándar Hellenia |
| Filestore huérfanos post-clon | P3 | Limpiar attachments legacy si afectan reportes |

---

## 9. Certificación

```
PROMOCIÓN TEST:     EXITOSA
Commit:             b700010
PHASE6_MVP TEST:    ok: true
Hardening:          ok: true
Concurrencia NCF:   PASS
UAT en TEST:        HABILITADO
Restauración:       No requerida (backup 2026-06-30_1218 disponible)
Fecha:              2026-06-30
```

---

## 10. Rollback (si fuera necesario)

```bash
./scripts/restore-test.sh /opt/odoo-projects/hellenia/backups/test/2026-06-30_1218
```

No ejecutado — promoción exitosa.
