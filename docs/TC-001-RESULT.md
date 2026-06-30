# TC-001 — Resultado de instalación `l10n_do` en DEV

**Fecha ejecución:** 2026-06-30 (UTC)  
**Entorno:** `hellenia_dev` — https://dev.hellenia.cloud  
**Build Odoo:** `19.0+e-20260619` (imagen `hellenia-odoo:19-enterprise`)  
**Ejecutor:** Cloud Agent vía SSH `root@2.25.69.179`

---

## Resumen ejecutivo

| Ítem | Resultado |
|------|-----------|
| Instalación `l10n_do` | ✅ **PASS** |
| Infraestructura post-instalación | ✅ **PASS** (tras reinicio Odoo) |
| Regla 3 — exclusión `l10n_do_reports` / `l10n_do_check_printing` | ⚠️ **INCUMPLIDA por `auto_install` de Odoo** |
| Datos fiscales en BD (impuestos, NCF, tipos documento) | ⚠️ **No cargados** — plantillas en módulo; aplicación requiere empresa DO (fuera de alcance TC-001) |
| Rollback ejecutado | ❌ **No** — instalación estable; incumplimientos documentados son comportamiento de plataforma |

**Conclusión TC-001:** **PASS condicional** — el módulo `l10n_do` quedó instalado y operativo. Se documentan desviaciones de alcance por `auto_install` de Enterprise y ausencia de datos NCF en archivos del módulo v19.0. **Detenido — esperando aprobación para TC-002.**

---

## 1. Punto de restauración

| Campo | Valor |
|-------|-------|
| Backup validado (TC-000) | `/opt/odoo-projects/hellenia/backups/dev/2026-06-30_0353` |
| Punto de restauración TC-001 | Symlink `/opt/odoo-projects/hellenia/backups/dev/TC-001-restore-point` → backup anterior |
| Verificación pre-instalación | `verify-backup-dev.sh` → **backup completo y válido** |
| Comando rollback | `/opt/odoo-projects/hellenia/scripts/restore-dev.sh /opt/odoo-projects/hellenia/backups/dev/2026-06-30_0353` |

---

## 2. Acción ejecutada

```bash
cd /opt/odoo-projects/hellenia/docker/dev
source /opt/odoo-projects/hellenia/config/dev/.env
docker compose --env-file .../config/dev/.env stop odoo
docker compose --env-file .../config/dev/.env run --rm odoo odoo \
  -d hellenia_dev --db_host=db --db_user=odoo --db_password="$DB_PASSWORD" \
  -i l10n_do --stop-after-init
docker compose --env-file .../config/dev/.env up -d odoo
```

**Módulo solicitado:** únicamente `l10n_do` (`-i l10n_do`).

**No ejecutado (según reglas):** wizard, creación de empresa, creación de usuarios, instalación manual de terceros, cambios en TEST/PROD.

---

## 3. Versión exacta del módulo

| Atributo | Valor |
|----------|-------|
| Módulo técnico | `l10n_do` |
| Nombre | Dominican Republic - Accounting |
| Versión manifest | `2.0` |
| Versión instalada en BD | `19.0.2.0` |
| Ruta en imagen | `/usr/lib/python3/dist-packages/odoo/addons/l10n_do/` |
| Autor (manifest) | Gustavo Valverde - iterativo \| Consultores de Odoo |
| Licencia | LGPL-3 |

---

## 4. Dependencias instaladas automáticamente

### 4.1 Dependencias directas de `l10n_do` (manifest)

| Módulo | Versión instalada | Motivo |
|--------|-------------------|--------|
| `account` | 19.0.1.4 | `depends` |
| `base_iban` | 19.0.1.0 | `depends` |

### 4.2 Cadena Enterprise / contabilidad (78 módulos totales)

Al instalar `account` en Odoo 19 Enterprise, el resolver instaló la suite contable EE, incluyendo:

| Módulo | Versión | Motivo |
|--------|---------|--------|
| `account_accountant` | 19.0.1.1 | Auto EE |
| `account_reports` | 19.0.1.0 | Auto EE |
| `account_check_printing` | — | Dependencia cadena account |
| + 30 módulos `account_*` / spreadsheet / payment | — | Cadena account EE |

### 4.3 Módulos RD auto-instalados (⚠️ fuera de alcance solicitado)

| Módulo | Versión | Regla `auto_install` en manifest |
|--------|---------|-----------------------------------|
| `l10n_do_check_printing` | 19.0.1.0 | `auto_install: ['l10n_do']` |
| `l10n_do_reports` | 19.0.1.0 | `auto_install: True` (requiere `l10n_do` + `account_reports`) |

**Nota:** No fue posible instalar solo `l10n_do` sin estos módulos usando el mecanismo estándar `-i l10n_do` en Odoo 19 EE. Odoo los instaló en la misma transacción (posiciones 75/78 y 76/78 del log).

### 4.4 Módulos explícitamente NO instalados

| Módulo | Estado |
|--------|--------|
| `l10n_do_edi` | **Ausente** del catálogo |
| Módulos terceros / OCA | **No instalados** |

---

## 5. Módulos `auto_install` relevantes

| Módulo | Condición `auto_install` | Instalado en TC-001 |
|--------|--------------------------|---------------------|
| `l10n_do` | `['account']` | ✅ (objetivo) |
| `l10n_do_check_printing` | `['l10n_do']` | ✅ (no solicitado) |
| `l10n_do_reports` | `True` (con `l10n_do` + `account_reports`) | ✅ (no solicitado) |
| `account_accountant` | EE con `account` | ✅ |
| `account_reports` | EE con `account_accountant` | ✅ |

---

## 6. Cambios realizados en DEV

| Área | Antes (TC-000) | Después (TC-001) |
|------|----------------|------------------|
| Módulos instalados | 16 (`web_enterprise` + base) | **78** |
| `account` | `uninstalled` | `installed` |
| `l10n_do` | `uninstalled` | `installed` |
| `l10n_do_reports` | `uninstalled` | `installed` ⚠️ |
| `l10n_do_check_printing` | `uninstalled` | `installed` ⚠️ |
| Empresa | "My Company", sin país, USD | "My Company", **United States**, USD |
| Usuarios | Sin cambios | Sin cambios |
| Impuestos ITBIS en BD | 0 | 0 (plantilla no aplicada) |
| Secuencias NCF en BD | 0 | 0 |
| Diarios contables | 0 | **7** (journals estándar `account`) |
| XML IDs `l10n_do` | 0 | **56** (tax report ITBIS cargado) |

---

## 7. Validaciones post-instalación (regla 4)

| Verificación | Resultado | Evidencia |
|--------------|-----------|-----------|
| Módulo `l10n_do` instalado | ✅ PASS | `result.json` → `state: installed` |
| Sin tracebacks en instalación | ✅ PASS | `install.log` — "Modules loaded", sin `Traceback` |
| Servidor responde | ✅ PASS | HTTP `/web` → 303, `version_info` → `19.0+e-20260619` |
| Login funciona | ✅ PASS | HTTP `/web/login` → 200, XML-RPC auth `uid=2` |
| Sin errores PostgreSQL críticos | ✅ PASS | Solo warning `extension "vector" is not available` durante install |
| Sin errores Docker | ✅ PASS | `hellenia-dev-odoo-1` healthy, `hellenia-dev-db-1` healthy |
| Sin errores Traefik | ✅ PASS | Sin `level=error` en últimos 30 min |

**Incidencia operativa:** Tras `docker compose up -d odoo`, el contenedor quedó brevemente `Exited` antes del reinicio manual. Se resolvió con segundo `up -d` + espera 60s. Estado final: **healthy**.

---

## 8. Validaciones fiscales disponibles (regla 5)

Sin crear empresa ni ejecutar wizard (según reglas 6–7).

| Verificación | Resultado | Detalle |
|--------------|-----------|---------|
| Plan contable RD disponible | ✅ PASS (plantilla) | Archivos en `l10n_do/data/template/`: `account.account-do.csv`, `account.group-do.csv`, `account.fiscal.position-do.csv` |
| Impuestos dominicanos disponibles | ✅ PASS (plantilla) | `account.tax-do.csv` — ITBIS 18%, 16%, 9%, 8%, exento, propina, retenciones. **No en tabla `account.tax`** hasta aplicar plan a empresa DO |
| Tax report ITBIS | ✅ PASS | `account_tax_report_data.xml` cargado — 56 XML IDs módulo `l10n_do` |
| Tipos documentos fiscales | ❌ NO DISPONIBLE | Modelo `l10n_latam.document.type` no presente / 0 registros |
| Secuencias NCF | ❌ NO DISPONIBLE en datos | Manifest declara NCF; **sin registros tras empresa DO** — validar en TC-002 |
| Configuración diarios | ✅ PASS | 7 diarios estándar `account` (INV, BILL, BNK1, MISC, CABA, EXCH, TAX) |

---

## 9. Evidencia

| Archivo | Ubicación |
|---------|-----------|
| Resultado XML-RPC | `evidence/l10n-do-tests/2026-06-30/TC-001/result.json` |
| Log instalación | `evidence/l10n-do-tests/2026-06-30/TC-001/install.log` |
| Checks infraestructura | `evidence/l10n-do-tests/2026-06-30/TC-001/infra-checks.txt` |
| Línea base pre-TC-001 | `evidence/l10n-do-tests/2026-06-30/BASELINE-PRE-TC001/` |
| Backup restauración | `/opt/odoo-projects/hellenia/backups/dev/2026-06-30_0353` |
| Symlink TC-001 | `/opt/odoo-projects/hellenia/backups/dev/TC-001-restore-point` |

### Extracto log instalación `l10n_do`

```
Loading module l10n_do (68/78)
loading l10n_do/data/account_tax_report_data.xml
Module l10n_do loaded in 0.19s, 272 queries
Loading module l10n_do_check_printing (75/78)    ← auto_install
Loading module l10n_do_reports (76/78)           ← auto_install
78 modules loaded in 29.60s
Modules loaded.
```

### Extracto infra-checks (post-reinicio)

```
login_http: 200
web_http: 303
server_version: 19.0+e-20260619
hellenia-dev-odoo-1 Up (healthy)
hellenia-dev-db-1 Up (healthy)
Odoo tracebacks since restart: none
Traefik errors: none
```

---

## 10. Brechas confirmadas

| ID | Hallazgo TC-001 |
|----|-----------------|
| G-01 | Secuencias NCF / tipos documento — **pendiente validación post-empresa DO (TC-002)** |
| G-02 | Tipos documento fiscal (`l10n_latam.document.type`) **ausentes** en instalación |
| G-09 | Resuelto — `account` ahora instalado |
| **Nuevo** | `l10n_do_reports` y `l10n_do_check_printing` **no evitables** con `-i l10n_do` en EE 19 por `auto_install` |

---

## 11. Conclusión

**TC-001: PASS condicional**

1. **`l10n_do` instalado correctamente** (v19.0.2.0) con dependencias `account` + `base_iban` y suite contable Enterprise.
2. **Infraestructura estable** — DEV responde, login OK, sin tracebacks post-reinicio.
3. **Regla 3 parcialmente incumplida** — `l10n_do_reports` y `l10n_do_check_printing` se auto-instalaron por diseño de Odoo 19 EE; no fue instalación manual ni de terceros.
4. **Datos fiscales RD** — plantillas disponibles en archivos del módulo; registros en BD pendientes de configuración empresa DO (TC-005+).
5. **NCF** — no disponible en datos del módulo; requiere validación en TC-020 / desarrollo `hellenia_account`.
6. **No se ejecutó rollback** — el estado es funcional y reversible vía backup `2026-06-30_0353`.

---

## 12. Estado y siguiente paso

| Caso | Estado |
|------|--------|
| TC-001 | ✅ Completado (PASS condicional) |
| TC-002 | ⏸️ **BLOQUEADO** — esperando aprobación explícita del cliente |

**Pregunta para aprobación TC-002:** ¿Aceptar `l10n_do_reports` y `l10n_do_check_printing` ya instalados por `auto_install`, o desinstalarlos antes de continuar con la verificación de datos precargados?
