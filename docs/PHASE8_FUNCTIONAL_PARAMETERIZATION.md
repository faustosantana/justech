# Fase 8 — Parametrización Funcional Completa

**Cliente:** Hellenia, S.R.L.  
**Ambiente:** DEV (`hellenia_dev`) — https://dev.hellenia.cloud  
**Fecha:** 2026-06-30  
**Rama:** `feature/justech-l10n-do-mvp`  
**Estado:** **COMPLETADA** — esperando aprobación para UAT funcional

---

## 1. Resumen ejecutivo

La Fase 8 transiciona el proyecto de desarrollo a **parametrización funcional**. Se auditó y parametrizó el ERP en DEV mediante configuración estándar Odoo, sin modificar módulos custom, core ni Enterprise.

| Bloque | Resultado | Documento |
|--------|-----------|-----------|
| 1 — Configuración general | PASS CON OBSERVACIONES | Este documento §2 |
| 2 — Comercial | PASS CON OBSERVACIONES | [COMMERCIAL_CONFIGURATION.md](COMMERCIAL_CONFIGURATION.md) |
| 3 — Compras | PASS CON OBSERVACIONES | [PURCHASE_CONFIGURATION.md](PURCHASE_CONFIGURATION.md) |
| 4 — Inventario | PASS CON OBSERVACIONES | [INVENTORY_CONFIGURATION.md](INVENTORY_CONFIGURATION.md) |
| 5 — Productos | PASS CON OBSERVACIONES | [PRODUCT_MASTER_MODEL.md](PRODUCT_MASTER_MODEL.md) |
| 6 — Contabilidad | PASS CON OBSERVACIONES | [ACCOUNTING_CONFIGURATION.md](ACCOUNTING_CONFIGURATION.md) |
| 7 — Localización RD | PASS | [DOMINICAN_LOCALIZATION_CONFIGURATION.md](DOMINICAN_LOCALIZATION_CONFIGURATION.md) |
| 8 — Reportes | PASS CON OBSERVACIONES | [REPORT_CATALOG.md](REPORT_CATALOG.md) |
| 9 — Sistema | PASS CON OBSERVACIONES | [SYSTEM_CONFIGURATION_AUDIT.md](SYSTEM_CONFIGURATION_AUDIT.md) |
| 10 — Datos piloto | PASS CON OBSERVACIONES | [UAT_READINESS_REPORT.md](UAT_READINESS_REPORT.md) |

**Resultado global:** **PASS CON OBSERVACIONES**

**Backup pre-Fase 8:** `/opt/odoo-projects/hellenia/backups/dev/2026-06-30_1400` — verificado.

**Evidencia:** `evidence/phase8-audit-dev.json`, `evidence/phase8-apply-dev.json`

---

## 2. Bloque 1 — Configuración general

### 2.1 Parametrizado

| Parámetro | Valor | Estado |
|-----------|-------|--------|
| Razón social | Hellenia, S.R.L. | ✅ |
| RNC | 133621282 | ✅ |
| País / moneda | DO / DOP | ✅ |
| Idioma | `es_DO` activo | ✅ |
| Zona horaria | `America/Santo_Domingo` | ✅ |
| Dirección oficial | Federico Geraldino / Piantini | ✅ |
| Teléfono / email | +1 849-434-8694 / info@helleniadr.com | ✅ |
| Website | https://hellenia.cloud | ✅ |
| Logo | Configurado | ✅ |
| Bancos | López de Haro DOP + USD | ✅ |
| `web.base.url` | https://dev.hellenia.cloud | ✅ |
| Fiscal Justech | Habilitado | ✅ |

### 2.2 Pendiente (no inventado)

| Item | Prioridad | Responsable |
|------|-----------|-------------|
| Favicon personalizado | P2 | Hellenia / diseño |
| Pie de documentos (texto legal) | P1 | Hellenia |
| Firmas en reportes PDF | P2 | Hellenia |
| SMTP y alias correo | P1 | Justech + Hellenia IT |
| Sucursales adicionales | P3 | Hellenia (si aplica) |

### 2.3 Validación

```
Estado: PASS CON OBSERVACIONES
```

---

## 3. Acciones aplicadas (Fase 8)

Script: `scripts/apply-phase8-parameterization.py` — 15 acciones idempotentes:

| Acción | Detalle |
|--------|---------|
| Fiscal habilitado | `justech_do_fiscal_enabled=True` |
| Empresa actualizada | Golden Configuration re-aplicada |
| Plazos de pago | Pago inmediato, 15/30/45/60 días |
| Equipo comercial | Ventas Hellenia |
| Lista de precios | Lista pública DOP |
| Diarios NCF | INV + FACTU con `justech_do_use_ncf` |
| Datos piloto | UAT-PILOT-CUST/VEND/PROD-001 |
| Parámetro web | `web.base.url` confirmado |

---

## 4. Restricciones respetadas

| Restricción | Cumplimiento |
|-------------|--------------|
| No nuevas funcionalidades | ✅ |
| No modificar arquitectura/core/Enterprise | ✅ |
| No nuevos módulos | ✅ |
| No tocar TEST | ✅ |
| No tocar PRODUCCIÓN | ✅ |
| No usuarios funcionales | ✅ |
| No catálogo real | ✅ |
| No iniciar UAT | ✅ |
| Cambios reversibles y documentados | ✅ |

---

## 5. Validaciones post-parametrización

| Validación | Resultado |
|------------|-----------|
| `PHASE35_VALIDATION` | ✅ `ok: true` |
| `PHASE6_MVP` | ✅ `ok: true` (19 checks) |
| Auditoría Fase 8 | ✅ PASS CON OBSERVACIONES |

---

## 6. Certificación Fase 8

| Dimensión | Estado |
|-----------|--------|
| Configuración general | PASS CON OBSERVACIONES |
| Comercial | PASS CON OBSERVACIONES |
| Compras | PASS CON OBSERVACIONES |
| Inventario | PASS CON OBSERVACIONES |
| Productos (modelo maestro) | PASS CON OBSERVACIONES |
| Contabilidad | PASS CON OBSERVACIONES |
| Localización dominicana | **PASS** |
| Reportes | PASS CON OBSERVACIONES |
| Sistema | PASS CON OBSERVACIONES |
| Datos piloto | PASS CON OBSERVACIONES |

### Pendientes antes del UAT

1. Aprobación explícita Hellenia para iniciar UAT  
2. SMTP corporativo  
3. Pie de documentos y textos legales  
4. Rangos NCF DGII reales (autorización Hellenia)  
5. Políticas comerciales (descuentos, devoluciones, garantías)  
6. Crear usuarios funcionales según [ROLE_MATRIX.md](ROLE_MATRIX.md)  
7. Cargar catálogo piloto ampliado (opcional, acordado con Hellenia)

### Pendientes antes del Go-Live

Ver [GO_LIVE_READINESS.md](GO_LIVE_READINESS.md) — stack producción, licencia, migración.

### Riesgos

| ID | Riesgo | Severidad |
|----|--------|-----------|
| P8-R01 | Sin SMTP — notificaciones UAT limitadas | Media |
| P8-R02 | Rangos NCF de prueba en DEV — no válidos DGII | Baja (DEV) |
| P8-R03 | Políticas comerciales sin definir | Media |
| P8-R04 | Categorías legacy Fase 3 coexisten con oficiales | Baja |

### Recomendaciones

1. Iniciar UAT en **TEST** tras clonación DEV→TEST y aprobación.  
2. Configurar SMTP antes de escenarios con correo.  
3. Obtener rangos NCF autorizados de DGII antes de facturación real.  
4. Validar plan contable con contador Glys Nuñez.  
5. Limpiar registros `PHASE4-*` de prueba o marcarlos como obsoletos en UAT.

---

## 7. Comandos de reproducción

```bash
# Flujo completo Fase 8 (solo DEV)
./scripts/run-phase8-parameterization.sh dev

# Componentes individuales
./scripts/backup-dev.sh
./scripts/apply-phase8-parameterization.sh dev
./scripts/audit-phase8-functional.sh dev
./scripts/validate-phase35-golden-config.sh dev
./scripts/validate-phase6-mvp.sh dev
```

---

## 8. Referencias

- [UAT_READINESS_REPORT.md](UAT_READINESS_REPORT.md)
- [PHASE75_CERTIFICATION.md](PHASE75_CERTIFICATION.md)
- [ROLE_MATRIX.md](ROLE_MATRIX.md)
- `config/company/*.yaml`

---

**Detenido.** Esperando aprobación para iniciar UAT funcional.
