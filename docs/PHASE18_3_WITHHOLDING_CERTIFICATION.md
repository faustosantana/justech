# Fase 18.3 — Certificación final motor retenciones RD

**Ejecutado en VPS TEST:** Sí — `srv.hellenia.cloud` / `hellenia_test`  
**Rama desplegada:** `cursor/phase18-3-withholding-certification-dd85`  
**Commit:** `c0838d0` (incluye Fase 18.2 + fix upgrade catálogo)  
**Módulo:** `hellenia_account` **19.0.1.0.7**  
**Timestamp UTC:** 2026-06-30T20:56:45Z

---

## Veredicto

| Métrica | Resultado |
|---------|-----------|
| **TEST** | **PASS** |
| Checks certificación | **23 / 23** |
| Producción | **NO promover** sin aprobación explícita |

---

## Backup TEST previo

| Campo | Valor |
|-------|-------|
| Script | `./scripts/backup-test.sh` |
| Ruta | `/opt/odoo-projects/hellenia/backups/test/2026-06-30_2054` |
| Contenido | PostgreSQL dump, filestore, custom.tar.gz, docker-compose, .env |
| `verify-backup-test.sh` | No existe en repo; backup verificado por MANIFEST y listado de archivos |

---

## Nota sobre rama 18.2 pura

La rama `cursor/phase18-2-withholding-catalog-dd85` (`8d79831`) **falló el upgrade** en TEST:

```text
ParseError: La retención «Retención ITBIS 30% Profesional» debe tener cuenta contable antes de activarse.
```

La certificación real se ejecutó con **18.3** que corrige `sync_catalog_from_taxes` (`active=False` al crear). Funcionalidad 18.2 validada al 100% tras el fix.

---

## Evidencia

| Archivo | Descripción |
|---------|-------------|
| `evidence/phase18-3/phase18-3-withholding-certification-test.json` | JSON 23 checks PASS |
| `evidence/phase18-3/01-catalogo-activo.html` | 7 retenciones activas + cuentas |
| `evidence/phase18-3/07-selector-filtros.html` | 5 cliente / 6 proveedor |
| `evidence/phase18-3/17-reportes-fiscales.html` | 606/607 con NCF |
| `evidence/phase18-3/18-19-historial.html` | Factura + pago + retención |
| `evidence/phase18-3/22-estilo-odoo.html` | Menú Localización Dominicana |

---

## Cuentas contables verificadas (TEST)

| Código | Cuenta |
|--------|--------|
| RET-GOB-5 | 11080302 |
| RET-ITBIS-30 / RET-ITBIS-100 | 21030201 |
| RET-INF-ISR-10 | 21030301 |
| RET-INF-ITBIS-75 | 21030205 |
| RET-ISR-2 | 21030308 |
| RET-HON-10 | 21030302 |

---

## Regresión

| Suite | Resultado |
|-------|-----------|
| Fase 18.2 | PASS 23/23 |
| Fase 18 motor | PASS 18/18 |
| Fase 16 pagos/bancos | PASS 23/23 |
| Fase 17.4 wizard | 17/18 — `withholdings_section` legado pre-Fase 18 |

---

## Comando re-ejecución

```bash
cd /opt/odoo-projects/hellenia
git checkout cursor/phase18-3-withholding-certification-dd85
./scripts/backup-test.sh
./scripts/run-phase18-2-test.sh
./scripts/run-phase18-3-certify-test.sh
```
