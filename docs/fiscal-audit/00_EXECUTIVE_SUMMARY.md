# 00 — Resumen ejecutivo — Auditoría maestra fiscal dominicana

**Fecha:** 2026-07-17 (UTC)  
**Ámbito:** SOLO DEV — cero cambios funcionales  
**Producción modificada:** NO  
**Baseline NCF intacta:** SÍ (`aaea7f5f4730a038f005a3e6010354f9da64963a` / tag `ncf-alerts-baseline-v1`)

## Veredicto

Auditoría **COMPLETA** a nivel inventario + diagnóstico + plan.  
Estado operativo DEV: **estable con deuda fiscal estructural** (doble stack Adel/LATAM + Justech).  
**No iniciar remediaciones** sin autorización expresa.

## Entorno

| Ítem | Valor |
|---|---|
| Host DEV | `207.244.242.58` (`vmi3364393`) |
| Dominio | `erp.justech.do` |
| BD | `justech_dev` |
| Servicio | `odoo-dev.service` |
| Odoo | `19.0-20260324` |
| PostgreSQL | `16.14` |
| Backup | `/opt/odoo-dev/backups/fiscal-master-audit-20260717_032503` |
| Restore test | **PASS** |

## Módulos núcleo

| Módulo | Versión DB/disk |
|---|---|
| `justech_l10n_do_base` | 19.0.1.26.0 |
| `justech_l10n_do_ncf` | 19.0.2.14.0 |
| `justech_l10n_do_reports` | 19.0.1.24.5 |

## Hallazgos (conteo)

| Severidad | Cantidad |
|---|---|
| CRÍTICO | 1 |
| ALTO | 5 |
| MEDIO | 8 |
| BAJO | 4 |
| Descartados / falso positivo | 2 |

## Hallazgos clave

1. **FISC-AUD-001 (CRÍTICO):** Coexistencia Adel/LATAM dominante vs Justech (`justech_do_*`) casi vacío en documentos publicados → riesgo de reportes/validaciones leyendo campos distintos.
2. **FISC-AUD-002 (ALTO):** 20 documentos con prefijo NCF ≠ tipo LATAM (ej. B02 en tipo B01, PROFORMA14, E31 vs B15).
3. **FISC-AUD-003 (ALTO):** Grupos Responsable/Usuario Fiscal con **0 usuarios**; solo 1 Administrador Fiscal.
4. **FISC-AUD-004 (ALTO):** Cron Adel `FISCAL SEQUENCE: Expire sequences` activo en paralelo al motor Justech.
5. Duplicados naive company+NCF: **falso positivo** (alcance v2.0 venta/compra). Duplicados reales venta o compra+proveedor: **0**.

## Controles verdes

- GL balanceado (`diff=0`).
- Rangos: sin solapes, sin next fuera de bounds, sin active+agotado matemático.
- Alertas NCF baseline: cron activo, 0 correos NCF, 0 actividades NCF abiertas.
- Restore test PASS.
- Producción no tocada.

## Próximo paquete recomendado

**P0 — Dual-stack NCF truth source:** definir fuente canónica (LATAM vs Justech), reconciliación FDP, y bloqueo tipo≠prefijo en publicación (ya parcialmente en compras recibidas).

Ver: `15_REMEDIATION_PLAN.md`, `14_FINDINGS_REGISTER.md`.
