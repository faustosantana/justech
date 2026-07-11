# GO_LIVE_CERTIFICATION — Justech Fiscal v1.0

**Fecha:** 2026-07-11  
**Entorno certificado:** `erp.justech.do` / BD `justech_dev`  
**Rama:** `feature/fiscal-standard-consolidation`  
**Producción (`justgroup.app`):** no tocada  

---

## Resumen ejecutivo

Se ejecutó el Gate Final de Producción (Gates 1–5) sobre el stack Justech Fiscal en el entorno de desarrollo/pruebas. Los cinco Gates resultaron **PASS** tras correcciones puntuales de datos/configuración (sin desarrollo de funcionalidades nuevas).

**Recomendación final:** Listo con observaciones — apto para planificar despliegue controlado a Producción **solo tras** cumplir `CHECKLIST_PRE_PRODUCCION.md` y aprobación explícita del propietario.

---

## Resultado por Gate

| Gate | Nombre | Resultado |
|------|--------|-----------|
| 1 | Datos | **PASS** |
| 2 | Operación | **PASS** |
| 3 | Seguridad | **PASS** |
| 4 | Infraestructura | **PASS** |
| 5 | Go-Live (documentación) | **PASS** |

---

### Gate 1 — Datos — PASS

- 4 empresas; 11 tipos de comprobante; 9 rangos activos/empresa.
- Padrón global: **781,980** RNC; integridad **green**; sin duplicados de RNC.
- Sin facturas posted sin NCF (hard empty).
- Salud operativa limpia (`POSTED_MISSING_NCF`, `PARTNER_INVALID_RNC`, `PADRON_ISSUE` = 0).
- FDP resuelve NCF; gap histórico Adel→Justech documentado (**460** out_invoice con latam y sin `justech_do_ncf`; health `POSTED_HISTORICAL_ADEL_NCF` = 107 informativo).

**Correcciones:** 3 facturas demo sin NCF → B02 asignado; partner 2170 `is_company=True`; issues stale resueltos.

### Gate 2 — Operación — PASS

- Ventas E2E: cotización→pedido→entrega→factura **FC/2026/00398** NCF **B0105185346**→cobro→GL balanceado→607 generado.
- Compras E2E: OC→recepción→factura **FP/2026/07/0020** NCF **B1191230000**→pago→GL balanceado→606 generado.
- Capacidad de retención/withholding presente; menús fiscales OK; login HTTP 200.
- Sin errores de flujo en shell (RPC/Access en caminos certificados).

### Gate 3 — Seguridad — PASS

- Perfiles UAT validados en 4 empresas: Admin Sistema, Admin Fiscal, Responsable, Usuario Fiscal, Contador, Ventas, Compras.
- Sin cruce multiempresa en lecturas con `allowed_company_ids` de una sola empresa.
- ACL Justech presentes (42 modelos); Centro Fiscal denegado correctamente a Ventas/Compras.
- **Corrección:** Contador UAT sin grupo fiscal → se asignó `group_justech_do_fiscal_manager` (Responsable Fiscal) según catálogo `ROLE-CONTADOR` / FISC-DGII-*.

### Gate 4 — Infraestructura — PASS

- Backup completo: `/opt/odoo-dev/backups/gate-final-produccion-v1-20260711_200456/` (dump 75MB + filestore 362MB).
- Restore test a `justech_gate4_restore`: 4 companies, 781980 padrón, 2545 posted → **PASS** → DB descartada.
- Histórico de dumps incrementales/por tarea en `/opt/odoo-dev/backups/`.
- Logs (últimas 5000 líneas): **0 ERROR/CRITICAL**, 351 WARNING, 0 Traceback.
- Crons fiscales activos sin fallos: padrón DGII, secuencia fiscal, currency, audit, garantías.
- Mail: excepciones DEV canceladas (380); Mail Queue Manager **inactivo por diseño en DEV** (activar en PROD).
- Servicio `odoo-dev` active; workers 2; memoria OK; disco 41%.

### Gate 5 — Go-Live — PASS

Documentación generada (este paquete).

---

## Observaciones

1. Gap histórico NCF Adel sin backfill masivo (diseño de producto; FDP lee ambos).
2. En DEV la mayoría de crons Odoo Enterprise permanecen inactivos a propósito; PROD debe activar el set operativo del checklist.
3. Correos deshabilitados/cola cancelada en DEV; SMTP PROD requiere validación real.
4. Contador en PROD debe incluir grupo Responsable Fiscal (o matriz equivalente).
5. `justech_dev` certifica stack Justech; módulos Hellenia no son parte de esta certificación.

## Riesgos residuales

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| Declaración 606/607 con datos incompletos de operación | Medio | Checklist primer día + revisión Contador |
| Activación incorrecta de crons/correo en PROD | Alto | Checklist pre-prod + ventana controlada |
| Despliegue sin backup PROD validado | Crítico | Plan despliegue / rollback |

---

## Recomendación final

- [ ] Listo para Producción.
- [x] **Listo con observaciones.**
- [ ] No listo para Producción.

**Condición:** Aprobado para **planificar** salida a Producción bajo despliegue controlado; **no** ejecutar merge/despliegue a `justgroup.app` sin aprobación explícita del propietario y checklist pre-producción completo.
