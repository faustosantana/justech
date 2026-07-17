# 14 — Registro de hallazgos

## Resumen

| Severidad | IDs |
|---|---|
| CRÍTICO | FISC-AUD-001 |
| ALTO | FISC-AUD-002, 003, 004, 010, 014 |
| MEDIO | FISC-AUD-011, 012, 013, 020, 021, 030, 031, 032 |
| BAJO | FISC-AUD-040, 041, 042, 043 |
| Descartados | FISC-AUD-X01, X02 |

---

### FISC-AUD-001 — Dual stack NCF (LATAM dominante / Justech residual)
- **Severidad:** CRÍTICO  
- **Módulo:** base + ncf + l10n_do_accounting  
- **Evidencia:** SQL `ncf_latam_stats` — 1540 LATAM vs 1 Justech; 1539 posted sin justech type  
- **Esperado:** fuente fiscal canónica clara  
- **Observado:** operación vía LATAM; campos Justech casi vacíos  
- **Impacto:** validaciones/reportes pueden divergir  
- **Estado:** confirmado  
- **Baseline afectada:** NO  
- **Esfuerzo:** alto | **Rollback:** N/A (datos)

### FISC-AUD-002 — Prefijo NCF ≠ tipo documento (LATAM)
- **Severidad:** ALTO  
- **Evidencia:** 20 moves; muestras en `duplicates_scoped.txt`  
- **Impacto:** DGII / compliance  
- **Estado:** confirmado  
- **Baseline:** NO

### FISC-AUD-003 — Roles fiscales sin usuarios
- **Severidad:** ALTO  
- **Evidencia:** groups SQL — fiscal_user/manager = 0  
- **Impacto:** SoD, alertas en fallback  
- **Estado:** confirmado

### FISC-AUD-004 — Cron Adel expire sequences activo
- **Severidad:** ALTO  
- **Evidencia:** cron id 57 activo  
- **Impacto:** interferencia secuencias vs motor Justech  
- **Estado:** confirmado — requiere análisis Adel antes de desactivar

### FISC-AUD-010 — commits manuales en import padrón
- **Severidad:** ALTO  
- **Archivo:** `rnc_padron_import_service.py`  
- **Estado:** confirmado

### FISC-AUD-014 — FDP multi-fuente frágil ante dual stack
- **Severidad:** ALTO  
- **Archivo:** `fiscal_data_provider.py`  
- **Estado:** confirmado (diseño)

### FISC-AUD-011/012/013 — except amplio / sudo / limit=1
- **Severidad:** MEDIO — confirmado patrón; no todos son bugs

### FISC-AUD-020 — Umbrales idénticos 4 empresas
- **Severidad:** MEDIO — probable intencional

### FISC-AUD-021 — e-CF cron 1/min
- **Severidad:** MEDIO — requiere review carga/idempotencia

### FISC-AUD-030 — 608/609 sin evidencia operativa reciente
- **Severidad:** MEDIO — requiere reproducción

### FISC-AUD-031 — hellenia_account vs payments_withholding
- **Severidad:** MEDIO — probable interferencia si ambos activos

### FISC-AUD-032 — NCF lowercase (2)
- **Severidad:** MEDIO

### FISC-AUD-040–043 — docs, nomenclatura, inventarios, UX labels
- **Severidad:** BAJO

### FISC-AUD-X01 — Duplicados company+NCF naive
- **Estado:** **falso positivo** (v2.0 venta/compra)

### FISC-AUD-X02 — “justech_do_ncf vacío = NCF perdido”
- **Estado:** **falso positivo** — NCF está en LATAM number
