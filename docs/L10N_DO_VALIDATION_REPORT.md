# Informe de Validación Funcional — Localización Dominicana (Fase 2)

**Cliente:** Hellenia, S.R.L.  
**Ambiente:** `hellenia_dev` — https://dev.hellenia.cloud  
**Build:** `19.0+e-20260619`  
**Fecha ejecución:** 2026-06-30  
**Ejecutor:** Consultoría Justech (Cloud Agent)  
**Estado:** ⛔ **DETENIDO en TC-000** — backup completo no ejecutable sin acceso VPS

---

## Resumen ejecutivo

Se inició la ejecución del [Plan de Pruebas Fase 2](L10N_DO_TEST_PLAN.md) con autorización del cliente. **La ejecución se detuvo en TC-000** porque no fue posible ejecutar `backup-dev.sh` en el VPS (`2.25.69.179`): acceso SSH denegado (sin clave `HELLENIA_SSH_KEY` ni `HELLENIA_VPS_PASSWORD` en el entorno del agente).

Se verificó remotamente la línea base de DEV vía HTTPS/XML-RPC y se capturó evidencia JSON. **No se instaló ningún módulo** (`l10n_do`, `l10n_do_reports` siguen sin instalar).

| Métrica | Valor |
|---------|-------|
| Casos planificados | 32 |
| Casos ejecutados | 1 (TC-000 parcial) |
| PASS | 0 |
| FAIL | 0 |
| BLOCKED | 1 (TC-000 — backup) |
| PENDIENTE | 31 |

**Conclusión provisional:** La localización dominicana **no está certificada** para Etapa 1. Se requiere backup VPS verificado antes de continuar con TC-001.

---

## TC-000 — Resultado

| Campo | Valor |
|-------|-------|
| **Estado** | `BLOCKED` (backup) / línea base `PASS` parcial |
| **Fecha** | 2026-06-30 UTC |

### Objetivo

Punto de restauración + verificación prerrequisitos DEV.

### Pasos ejecutados

| # | Paso | Resultado |
|---|------|-----------|
| 1 | `backup-dev.sh` en VPS | ❌ No ejecutado — SSH `Permission denied` |
| 2 | `verify-backup-dev.sh` | ❌ No ejecutado — sin backup |
| 3 | Verificar Odoo 19 Enterprise | ✅ `19.0+e-20260619` |
| 4 | BD `hellenia_dev` | ✅ Autenticación XML-RPC OK |
| 5 | Módulos baseline | ✅ Capturado — ver abajo |
| 6 | `l10n_do_edi` ausente | ✅ No en catálogo módulos |
| 7 | HTTPS login | ✅ HTTP 200 |

### Resultado esperado vs obtenido

| Esperado | Obtenido |
|----------|----------|
| Backup postgres + filestore verificado | **No** — sin acceso shell VPS |
| `web_enterprise` instalado | ✅ `installed` |
| `account` instalado (prerrequisito plan) | ⚠️ **`uninstalled`** — desviación baseline |
| `l10n_do` / `l10n_do_reports` no instalados | ✅ `uninstalled` |
| `l10n_do_edi` no instalado | ✅ `absent` |

### Hallazgo baseline relevante

La BD `hellenia_dev` tiene **solo `web_enterprise` instalado** a nivel contable. El módulo `account` (Invoicing/Contabilidad) está **`uninstalled`**. Esto difiere del supuesto del plan (TC-000 paso 5). Antes de TC-001 habrá que instalar `account` (y probablemente `account_accountant` / `account_reports` para `l10n_do_reports`).

Empresa actual: **"My Company"**, país no configurado, moneda **USD** (no DOP).

### Evidencia

| Tipo | Ubicación |
|------|-----------|
| Snapshot JSON | `evidence/l10n-do-tests/2026-06-30/TC-000/result.json` |
| Script reutilizable | `scripts/run-l10n-do-functional-tests.py` |

### Conclusión TC-000

**BLOCKED** — No se cumple el gate de backup completo exigido por el cliente (regla 1). **No se autoriza continuar** con TC-001 hasta:

1. Ejecutar en VPS:
   ```bash
   cd /opt/odoo-projects/hellenia
   ./scripts/backup-dev.sh
   ./scripts/verify-backup-dev.sh
   ```
2. Confirmar ruta del backup (timestamp) al consultor.
3. Opcional: configurar `HELLENIA_SSH_KEY` o `HELLENIA_VPS_PASSWORD` en el entorno Cloud Agent para ejecución remota de backups futuros.

---

## Casos no ejecutados (TC-001 — TC-031)

Todos **PENDIENTE** por detención en TC-000.

| Caso crítico (bloqueante) | Estado |
|---------------------------|--------|
| Instalación `l10n_do` (TC-001) | PENDIENTE |
| Instalación `l10n_do_reports` (TC-003) | BLOCKED — upgrade Enterprise DEV pendiente |
| Plan contable (TC-007) | PENDIENTE |
| ITBIS (TC-010–011) | PENDIENTE |
| Diarios (TC-014–015) | PENDIENTE |
| Secuencias NCF (TC-017–020) | PENDIENTE |
| Asignación NCF (TC-020) | PENDIENTE |
| Factura cliente (TC-023–024) | PENDIENTE |
| Factura proveedor (TC-027) | PENDIENTE |
| Nota crédito (TC-025) | PENDIENTE |
| Impresión (TC-030) | PENDIENTE |
| Reportes fiscales (TC-031) | PENDIENTE |

---

## GAP confirmado (post TC-000)

| ID | Brecha | Estado | Evidencia |
|----|--------|--------|-----------|
| G-00 | Backup DEV no ejecutable desde Cloud Agent sin SSH VPS | **CONFIRMADO** | SSH denegado a `2.25.69.179` |
| G-09 | BD DEV sin `account` instalado — baseline no lista para `l10n_do` | **CONFIRMADO** | `result.json` TC-000 |
| G-00 | Backup DEV no ejecutable sin SSH VPS | **CONFIRMADO** | TC-000 — SSH denegado |
| G-09 | BD sin `account` instalado | **CONFIRMADO** | TC-000 — `result.json` |
| G-01 a G-08 | Brechas NCF/reportes | POR VALIDAR | Requiere TC-001+ |

Ver actualización en [GAP_ANALYSIS_RD.md](GAP_ANALYSIS_RD.md).

---

## Riesgos

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| Continuar sin backup | 🔴 Crítico | No instalar módulos hasta backup verificado |
| `account` no instalado | 🟠 Alto | Instalar `account` como primer paso post-backup |
| Empresa en USD sin país DO | 🟠 Alto | TC-005/006 tras instalar localización |
| Sin SSH para agente | 🟡 Medio | Proporcionar credenciales o ejecutar backup manual |

---

## Recomendaciones

1. **Inmediato:** Ejecutar backup manual en VPS y comunicar ruta timestamp.
2. **Reanudar ejecución** con mensaje: *"Backup TC-000 confirmado — ruta: `backups/dev/YYYY-MM-DD_HHMM`"*.
3. **Secuencia post-backup:** TC-001 instalará `account` si sigue ausente, luego `l10n_do`, `account_reports`, `l10n_do_reports`.
4. **No instalar** `l10n_do_edi` ni módulos terceros.
5. Configurar credenciales SSH en Cloud Agent para automatizar backups y evidencias en iteraciones siguientes.

---

## Certificación Etapa 1

| Criterio | Estado |
|----------|--------|
| NCF tradicional soportado con evidencia funcional | ❌ No certificado |
| Todos los casos críticos PASS | ❌ No iniciados |
| Localización certificada Etapa 1 | ❌ **Pendiente** |

---

## Referencias

- [L10N_DO_TEST_PLAN.md](L10N_DO_TEST_PLAN.md)
- [GAP_ANALYSIS_RD.md](GAP_ANALYSIS_RD.md)
- Evidencia: `evidence/l10n-do-tests/2026-06-30/TC-000/result.json`

---

**Versión:** 0.1 (ejecución parcial)  
**Próxima actualización:** Tras confirmación backup TC-000 y reanudación TC-001
