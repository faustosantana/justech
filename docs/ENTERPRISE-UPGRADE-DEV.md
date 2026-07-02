# Upgrade Enterprise DEV — Hellenia

**Estado:** Mantenimiento operativo — **no bloquea** implementación funcional ([PROJECT_STRATEGY.md](PROJECT_STRATEGY.md))  
**Alcance:** Solo `hellenia_dev` — **NO tocar TEST ni PRODUCCIÓN**  
**Fecha:** 2026-06-30

---

## Objetivo

Mantener DEV alineado con el **último paquete Enterprise 19.0** del portal Odoo. Tarea de infraestructura (Fase 2), independiente del avance funcional Fases 3–12.

---

## Estado actual (VPS — 2026-06-30)

| Componente | Valor |
|------------|-------|
| **DEV en ejecución** | `hellenia-odoo:19-enterprise` — Odoo `19.0-20260619` |
| **Tarball en disco (no desplegado)** | `/opt/odoo-projects/hellenia/downloads/enterprise/odoo_19.0+e.20260629.tar.gz` |
| **PKG-INFO tarball** | `19.0+e.20260629` |
| **SHA256 tarball** | `667ad231f9b9800ed2f06029d9c5c639af53c3255f94cca2e5643ee7502eb924` |
| **Tamaño** | 421 878 128 bytes (~402 MB) |
| **Archivos en `downloads/enterprise/`** | **1** (no hay descarga más reciente en VPS) |

### Conclusión versión

- La serie sigue siendo **Odoo 19.0** (no hay 19.1/20 en el portal para esta suscripción).
- El tarball `20260629` es **10 días más nuevo** que el build horneado en la imagen actual (`20260619`).
- **No existe** en el VPS otro archivo más reciente que `20260629`; si el portal ofrece uno nuevo, debe subirse manualmente.

### Módulos RD en tarball `20260629`

| Módulo | Estado en tarball |
|--------|-------------------|
| `l10n_do` | ✅ Presente |
| `l10n_do_reports` | ✅ Presente |
| `l10n_do_check_printing` | ✅ Presente |
| `l10n_do_edi` | ❌ Ausente (correcto Etapa 1) |
| `l10n_latam_base` | ✅ Presente |
| `l10n_latam_invoice_document` | ✅ Presente |
| `l10n_latam_check` | ✅ Presente |

> **Nota arquitectura:** En 19.0, `l10n_do` **no depende** de módulos LATAM. Las mejoras EDI/LATAM de `saas-19.3` no están backportadas a 19.0. Ver [L10N_DO_ARCHITECTURE_ANALYSIS.md](L10N_DO_ARCHITECTURE_ANALYSIS.md).

---

## Gate de aprobación

| Acción | Estado |
|--------|--------|
| Implementación funcional F3+ | 🔄 **En curso** — no esperar upgrade |
| `--execute` upgrade DEV | ⏸️ Opcional — cuando se confirme último tarball portal |
| TEST / PROD | 🔒 Sin cambios |
| Custom Justech | ⏸️ Solo tras 4 comprobaciones |

### Secuencia obligatoria (orden actual)

```
1. Verificación manual portal Odoo     ← ESTAMOS AQUÍ
2. Si no hay tarball > 20260629:
     aceptar 20260629 como último on-premise
3. upgrade-enterprise-dev.sh --execute  (solo tras paso 2)
4. Repetir TC-001 y TC-002 desde cero
5. Reevaluar G-01 con evidencia post-upgrade
6. Solo entonces: TC-003+
```

---

## Paso 0 — Verificación manual en portal Odoo (pendiente)

**Objetivo:** Confirmar si existe un paquete Enterprise **más reciente** que:

```
odoo_19.0+e.20260629.tar.gz
```

### Instrucciones para el usuario

1. Login en [odoo.com](https://www.odoo.com) (suscripción `M260616306091776`)
2. Ir a [odoo.com/page/download](https://www.odoo.com/page/download)
3. Seleccionar **Odoo 19** → **Enterprise** → fila **Sources** → **Download**
4. Anotar el **nombre exacto** del archivo (formato `odoo_19.0+e.YYYYMMDD.tar.gz`)
5. Comparar `YYYYMMDD` con `20260629`

| Resultado portal | Acción |
|------------------|--------|
| **Mismo** `20260629` o nombre idéntico | ✅ `20260629` es el último disponible → aprobar `--execute` con ese tarball |
| **Fecha mayor** que `20260629` (ej. `20260715`) | Subir nuevo tarball al VPS → `--validate-only` → luego `--execute` |
| **Duda** sobre el nombre | Adjuntar captura o pegar nombre en chat para validación |

> **No ejecutar `--execute`** hasta completar esta verificación y confirmar explícitamente en chat.

### Si `20260629` es el último

Mensaje de aprobación esperado (ejemplo):

> *Confirmado en portal: no hay paquete más reciente que 20260629. Proceder con upgrade DEV.*

Entonces Cursor ejecutará:

```bash
export HELLENIA_APPROVE_ENTERPRISE_EXECUTE=yes
/opt/odoo-projects/hellenia/scripts/upgrade-enterprise-dev.sh --execute \
  /opt/odoo-projects/hellenia/downloads/enterprise/odoo_19.0+e.20260629.tar.gz
```

> `--execute` está **bloqueado por defecto** hasta definir `HELLENIA_APPROVE_ENTERPRISE_EXECUTE=yes` tras tu confirmación explícita en chat.

Seguido de `--rerun-tc001-tc002` con backup pre-localización.

---

## Flujo cuando subas un nuevo paquete Enterprise

### Paso 1 — Entregar archivo al VPS

Elegir uno:

| Método | Comando |
|--------|---------|
| URL portal (temporal) | `scripts/download-enterprise-portal.sh 'URL'` |
| Adjuntar archivo | `HELLENIA_SSH_KEY=... scripts/receive-enterprise-archive.sh --upload /ruta/archivo.tar.gz` |
| Ya en VPS | Copiar a `/opt/odoo-projects/hellenia/downloads/enterprise/` |

### Paso 2 — Validar (sin instalar)

```bash
/opt/odoo-projects/hellenia/scripts/upgrade-enterprise-dev.sh --validate-only
# o con ruta explícita:
/opt/odoo-projects/hellenia/scripts/upgrade-enterprise-dev.sh --validate-only /opt/odoo-projects/hellenia/downloads/enterprise/odoo_19.0+e.YYYYMMDD.tar.gz
```

**Checklist automático:**

| # | Verificación |
|---|--------------|
| 1 | Integridad tar.gz (sin corrupción) |
| 2 | SHA256 registrado en reporte JSON |
| 3 | Versión PKG-INFO `19.0+e.YYYYMMDD` |
| 4 | Estructura `full_enterprise_source` (`odoo/addons/web_enterprise`) |
| 5 | `l10n_do` presente |
| 6 | `l10n_do_reports` presente |
| 7 | `l10n_do_edi` ausente (warn si presente — fuera Etapa 1) |
| 8 | Módulos `l10n_latam_*` inventariados |
| 9 | Modelos `l10n_latam*` escaneados en código |

Reportes en `logs/validate/`.

### Paso 3 — Comparar con DEV actual

```bash
/opt/odoo-projects/hellenia/scripts/upgrade-enterprise-dev.sh --status
```

### Paso 4 — Ejecutar upgrade (solo tras tu aprobación explícita)

```bash
/opt/odoo-projects/hellenia/scripts/upgrade-enterprise-dev.sh --execute /opt/odoo-projects/hellenia/downloads/enterprise/odoo_19.0+e.YYYYMMDD.tar.gz
```

**Secuencia automática:**

1. Validación RD completa
2. Backup DEV (`backup-dev.sh` + `verify-backup-dev.sh`)
3. Extracción tarball → build imagen `hellenia-odoo:19-enterprise`
4. Recrear contenedor DEV
5. Instalar/actualizar `web_enterprise`
6. `-u` módulos contables EE; `-u l10n_do*` si ya instalados
7. `validate-enterprise-dev.sh` + `healthcheck.sh`
8. Verificar TEST/PROD sin cambios
9. Rollback automático si falla

### Paso 5 — Repetir TC-001 y TC-002 desde cero

```bash
# Opcional: restaurar línea base pre-localización
export TC_BASELINE_BACKUP=/opt/odoo-projects/hellenia/backups/dev/2026-06-30_0353
/opt/odoo-projects/hellenia/scripts/upgrade-enterprise-dev.sh --rerun-tc001-tc002
```

Esto:

- Restaura backup (si `TC_BASELINE_BACKUP` definido)
- Ejecuta `-i l10n_do` (TC-001)
- Genera evidencia XML-RPC TC-001/TC-002

**TC-003 permanece bloqueado** hasta revisión manual de resultados TC-001/TC-002 post-upgrade.

---

## Scripts relacionados

| Script | Función |
|--------|---------|
| `upgrade-enterprise-dev.sh` | Orquestador principal (este documento) |
| `validate-enterprise-archive.sh --rd-stage1` | Validación tarball + RD |
| `report-enterprise-tarball.sh` | Estructura y tipo de tarball |
| `e1a-enterprise-image.sh` | Build imagen + backup + rollback |
| `receive-enterprise-archive.sh` | Recibir archivo sin SCP manual |
| `backup-dev.sh` / `restore-dev.sh` | Backup/restore DEV |
| `run-l10n-do-functional-tests.py` | Evidencia TC vía XML-RPC |

---

## Obtener versión más reciente del portal

Odoo no publica URL wget permanente para Enterprise. Pasos:

1. Login en [odoo.com](https://www.odoo.com) (suscripción `M260616306091776`)
2. [odoo.com/page/download](https://www.odoo.com/page/download) → Odoo 19 → Enterprise → **Sources** → Download
3. Entregar URL temporal o archivo a Cursor

Ver [E0.6c-ENTERPRISE-DELIVERY-FLOW.md](E0.6c-ENTERPRISE-DELIVERY-FLOW.md).

---

## Qué NO hacer

- ❌ Ejecutar TC-003 o pruebas NCF hasta DEV en última versión disponible
- ❌ Modificar `hellenia_test` ni producción
- ❌ Instalar `l10n_do_edi` (Etapa 1 = NCF tradicional)
- ❌ Asumir que un tarball más nuevo incluye B01–B13 o eNCF sin validar código

---

## Referencias

- [L10N_DO_TEST_PLAN.md](L10N_DO_TEST_PLAN.md) — plan de pruebas (TC-003 bloqueado)
- [L10N_DO_ARCHITECTURE_ANALYSIS.md](L10N_DO_ARCHITECTURE_ANALYSIS.md) — arquitectura RD 19.0 vs saas-19.3
- [GAP_ANALYSIS_RD.md](GAP_ANALYSIS_RD.md) — brechas NCF
- [E0.6b-ENTERPRISE-PORTAL-DOWNLOAD.md](E0.6b-ENTERPRISE-PORTAL-DOWNLOAD.md)

---

**Mantenido por:** Consultoría implementación Justech  
**Próximo paso:** **Verificación manual en portal Odoo** — comparar con `odoo_19.0+e.20260629.tar.gz`. No ejecutar `--execute` hasta confirmar.
