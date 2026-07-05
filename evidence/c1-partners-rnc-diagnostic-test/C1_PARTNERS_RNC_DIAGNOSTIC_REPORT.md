# C1 — Diagnóstico partners sin RNC (TEST)

**Ambiente:** `hellenia_test` (solo lectura)  
**Empresa:** Hellenia, S.R.L.  
**Fecha ejecución:** 2026-07-04 22:56 UTC-4  
**Modo:** read-only — sin create/write/unlink, sin PROD/DEV  
**Evidencia:** `evidence/c1-partners-rnc-diagnostic-test/`

---

## Resumen ejecutivo

El hallazgo **FISC-01** de la auditoría contable (235 facturas posted sin RNC) se confirma y se amplía con detalle por partner.

| Métrica | Valor | Notas |
|--------|------:|-------|
| Facturas cliente posted (`out_invoice`) sin RNC | **235** | Coincide con FISC-01 |
| Notas de crédito posted (`out_refund`) sin RNC | **19** | Todas del partner UAT 311 |
| **Total comprobantes** sin RNC | **254** | Alcance ampliado C1 vs auditoría |
| Partners distintos afectados | **48** | |
| Monto total afectado | **RD$ 945,159.56** | Jun 2026 – Jul 2026 |
| Con NCF asignado | **242** | 95.3% del universo |
| Sin NCF | **12** | 2 Phase4/5 + 10 Cliente Demo (ver C3) |
| % del total posted cliente | **76.0%** | 254 / 334 movimientos |

**Conclusión:** El problema es **casi enteramente datos de laboratorio/UAT** (41/48 partners, ~89% del monto). No hay evidencia de clientes reales de producción mezclados. Los 7 partners no clasificados como smoke son pruebas de concurrencia (4) o escenarios P199 (3) pendientes de confirmación.

**Impacto 607 real:** De 242 comprobantes con NCF sin RNC, **206 son B02 (consumidor final)** — el exportador 607 **no exige RNC** para esos prefijos. **36 comprobantes (17 B03 + 19 B04) sí bloquearían validación 607** si se incluyeran en un período de declaración.

---

## Reconciliación con auditoría previa

| Fuente | Conteo | Criterio |
|--------|-------:|----------|
| FISC-01 (`accounting-total-audit-readonly`) | 235 | Solo `out_invoice` posted sin `partner.vat` |
| C1 diagnóstico | 235 + 19 NC | Incluye `out_refund` del partner UAT 311 |
| C1 total | 254 | Universo completo ventas posted sin RNC |

---

## Tabla de partners afectados (48)

Ordenado por monto descendente. Detalle completo en `partners_affected.csv`.

| ID | Partner | Clasificación | Fact. | NC | Monto RD$ | Fechas | NCF | Diario | Tipos |
|---:|---------|---------------|------:|---:|----------:|--------|----:|--------|-------|
| 311 | UAT Cliente Consumidor Final | smoke_test | 169 | 19 | 527,203.56 | 06-30 – 07-03 | 179 | INV | 02/03/04 |
| 2361 | SMOKE P13.4 CF | smoke_test | 6 | 0 | 70,800.00 | 07-01 | 6 | INV | 02 |
| 2354 | Cliente cert 19.6 C1 | smoke_test | 3 | 0 | 35,400.00 | 07-01 | 3 | INV | 02 |
| 2355 | Cliente cert 19.6 C2 | smoke_test | 3 | 0 | 35,400.00 | 07-01 | 3 | INV | 02 |
| 2359 | Cliente cert 19.6 C6 | smoke_test | 3 | 0 | 35,400.00 | 07-01 | 3 | INV | 02 |
| 2362 | P199 H3 | review_required | 3 | 0 | 35,400.00 | 07-01 | 3 | INV | 02 |
| 2363 | P199 WEBSAVE | review_required | 3 | 0 | 35,400.00 | 07-01 | 3 | INV | 02 |
| 2364 | P199 WH | review_required | 3 | 0 | 35,400.00 | 07-01 | 3 | INV | 02 |
| 10 | Cliente prueba Fase 4 | smoke_test | 2 | 0 | 23,600.00 | 06-30 | 0 | INV | sin_tipo |
| 13 | PHASE5 Cliente Lab | smoke_test | 1 | 0 | 23,600.00 | 06-30 | 0 | INV | sin_tipo |
| 2360 | Cliente cert 19.6 C7 | smoke_test | 2 | 0 | 23,600.00 | 07-01 | 2 | INV | 02 |
| 2356–2358 | Cliente cert 19.6 C3–C5 | smoke_test | 1 c/u | 0 | 11,800 c/u | 07-01 | 1 c/u | INV | 02 |
| 407–436 | Cliente Demo 071–100 (30 pares) | smoke_test | 1 c/u | 0 | 944 c/u | 06-16 – 06-30 | 1 c/u | INV/PCC | 02 |
| 227, 229, 275 | Concurrent Worker 0 | incomplete_contact | 1 c/u | 0 | 59 c/u | 06-30 | 1 c/u | INV | 02 |
| 317 | Concurrent Worker 1 | incomplete_contact | 1 | 0 | 59.00 | 06-30 | 1 | INV | 02 |

**Agregados por clasificación**

| Clasificación | Partners | Facturas | NC | Monto RD$ | Con NCF |
|---------------|--------:|---------:|---:|----------:|--------:|
| smoke_test | 41 | 222 | 19 | 838,723.56 | 229 |
| review_required (P199) | 3 | 9 | 0 | 106,200.00 | 9 |
| incomplete_contact | 4 | 4 | 0 | 236.00 | 4 |
| **Total** | **48** | **235** | **19** | **945,159.56** | **242** |

**Duplicados detectados:** 1 cluster — `Concurrent Worker 0` (IDs 227, 229, 275). Candidatos a fusión.

**Diarios:** INV (250), PCC (4 — demos POS/concurrent).

**Tipos comprobante:** B02/02 (215), B03/03 (17), B04/04 (19 NC), sin_tipo (3).

---

## Clasificación de candidatos

### 1. Datos SMOKE / pruebas (41 partners — 241 movimientos)

- **UAT Cliente Consumidor Final (311):** volumen masivo UAT/Phase29 — 169 facturas + 19 NC, incluye secuencias B02, B03 y B04.
- **SMOKE / cert 19.6 / Phase4-5 / Cliente Demo NN:** nomenclatura explícita de laboratorio.
- **Riesgo operativo:** bajo para negocio real; **alto para secuencias NCF consumidas** en TEST.

### 2. Clientes reales

- **Ninguno identificado** con perfil `real_client_candidate` (volumen alto + monto alto sin patrón smoke).

### 3. Consumidor final

- Partner 311 y 2361 etiquetados también como `consumidor_final_candidate`.
- Mayoría B02 — **RNC no requerido para 607** según `justech.do.dgii.607.exporter._is_consumer_invoice`.
- Aun así conviene **partner CF maestro** con RNC genérico DGII para consistencia de datos.

### 4. Duplicados

- Cluster `Concurrent Worker 0` ×3 — mismo nombre, sin VAT, 1 factura c/u.

### 5. Contactos incompletos

- 4 partners de prueba de concurrencia (Worker 0/1), montos mínimos (RD$ 59).

### 6. Revisión manual (P199 — 3 partners)

- `P199 H3`, `P199 WEBSAVE`, `P199 WH` — escenarios Phase 19.9; no matchearon regex smoke (`P199` > 2 dígitos).
- **Recomendación:** reclasificar como smoke tras confirmación; 9 facturas B02 con NCF.

---

## Facturas fiscales posted con NCF pero sin RNC

**Total: 242** (223 facturas + 19 notas de crédito).

| Prefijo / tipo | Cantidad | ¿607 exige RNC? | Observación |
|----------------|--------:|:---------------:|-------------|
| B02 (consumidor) | 206 | No | Válidas para 607 sin RNC en partner |
| B03 (crédito fiscal) | 17 | **Sí** | Partner 311 UAT — bloquean validación |
| B04 (notas crédito) | 19 | **Sí** | NC UAT partner 311 |
| **Críticos 607** | **36** | | Ver `607_impact_breakdown.json` |

Muestras B03 críticas: `DINV/2026/00002` … `B0300020001` (partner 311, RD$ 100).

---

## Impacto en declaración 607

**Módulo:** `justech_l10n_do_reports` — validación en `_dgii_validate_single_move`:

- Si **no** es consumidor (`B02`, `B12`, `E32`, `E33`) **y** partner sin `vat` → **error 607**.
- Consumidor final → RNC omitido en validación.

**Estimación YTD 2026 (read-only):**

- 254 comprobantes sin RNC en el universo analizado
- Monto: RD$ 945,159.56
- Período julio 2026: no se ejecutó `validate_period_607` (módulo período no disponible en shell); estimación manual arriba.

**Si TEST se usara para generar 607 real:**

| Escenario | Resultado |
|-----------|-----------|
| Solo B02 sin RNC | Exportación posible (206 líneas) |
| Incluir B03/B04 sin corregir | **36 errores de validación** |
| Declaración formal DGII | **No procede** — ambiente TEST + NCF de prueba |

**Recomendación:** Excluir TEST de pipelines 607 productivos; en TEST, marcar partners/journals lab antes de cualquier export piloto.

---

## Riesgos fiscales

| ID | Severidad | Descripción |
|----|-----------|-------------|
| FISC-C1-01 | Crítica | 254 comprobantes posted sin RNC (76% del volumen cliente TEST) |
| FISC-C1-02 | Crítica | 242 con NCF asignado — secuencias fiscales consumidas sin identificación tributaria en partner |
| FISC-C1-03 | Alta | 36 comprobantes B03/B04 bloquean 607 si se exportan |
| FISC-C1-04 | Media | 1 cluster duplicado (Concurrent Worker 0) |
| FISC-C1-05 | Media | 12 comprobantes sin NCF además de sin RNC (solapamiento C3) |
| FISC-C1-06 | Baja | Contaminación de métricas de certificación si smoke no se segrega |

**Nota:** En TEST el riesgo es **metodológico y de certificación**, no de multa DGII, salvo que datos TEST se mezclen con PROD.

---

## Plan de corrección propuesto (NO EJECUTADO)

### A. smoke_test (41 partners, ~241 movimientos)

| Acción | Owner |
|--------|-------|
| Archivar partners lab (`active=False`) | Justech |
| Migrar facturas históricas a partner CF maestro con RNC `001-0000000-0` **o** mantener archivadas | Contador + Justech |
| Evaluar NC/anulación de B03/B04 UAT si secuencias no deben contar | Contador |
| Excluir journals `DINV`/lab de reportes 607 piloto | Justech config |
| No reutilizar secuencias NCF UAT en PROD | Gobernanza |

### B. consumidor_final_candidate (311, 2361)

| Acción | Owner |
|--------|-------|
| Unificar en **un partner CF maestro** con RNC genérico DGII | Contador |
| Verificar tipo B02 en comprobantes | Justech config |
| 19 NC B04: asignar RNC o vincular a factura origen corregida | Contador |

### C. duplicate_candidate (227, 229, 275)

| Acción | Owner |
|--------|-------|
| Fusionar en un partner; completar RNC CF o archivar | Justech merge + contador |

### D. incomplete_contact (317 + cluster)

| Acción | Owner |
|--------|-------|
| Completar ficha o archivar tras fusión | Justech |

### E. review_required — P199 (2362, 2363, 2364)

| Acción | Owner |
|--------|-------|
| Confirmar smoke Phase 19.9 → archivar o asignar RNC CF | Contador |
| 9 facturas B02: bajo riesgo 607; corregir partner igualmente | Justech |

### F. ncf_without_rnc — prioridad B03/B04 (36)

| Acción | Owner |
|--------|-------|
| Corregir partner antes de cualquier export 607 | Contador + Justech |
| Re-validar con `validate_period_607(refresh_states=False)` | Justech |

### G. Prevención futura

| Acción | Owner |
|--------|-------|
| Bloqueo pre-post: partner DO sin RNC válido (excepto CF explícito) | **Código** — `justech_l10n_do_ncf` / `hellenia_account` |
| Partner template smoke con tag `is_lab` + dominio en vistas | **Config** Justech |
| CI: fallar si facturas posted sin RNC en escenarios cert | **Código** scripts |

---

## Qué requiere contador

1. Confirmar tratamiento fiscal de comprobantes UAT con NCF (¿anular/NC o solo corrección partner en TEST?).
2. Aprobar RNC genérico consumidor final para partners CF/lab.
3. Revisar 9 facturas P199 (¿smoke o escenario válido?).
4. Decidir si B03 UAT (17) requieren NC formal o solo corrección de datos TEST.
5. Sign-off antes de C1 corrección masiva y antes de C6 PROD.

---

## Qué puede hacer Justech (configuración)

1. Archivar partners smoke identificados (lista en `c1-diagnostic.json` → `correction_plan.smoke_test.partner_ids`).
2. Crear/ usar partner **Consumidor Final** maestro con RNC DGII.
3. Fusionar duplicados `Concurrent Worker 0`.
4. Etiquetar diarios UAT (`DINV`, etc.) para exclusión en wizard 607.
5. Re-ejecutar validación 607 post-corrección (read-only).

---

## Qué requiere código (post-aprobación)

1. **Constraint pre-post:** impedir `action_post` en facturas DO si partner no es CF y no tiene RNC válido (`justech_do_has_rnc()`).
2. **Excepción CF:** flag en partner o tipo doc B02 con partner CF maestro obligatorio.
3. **Smoke guard:** en TEST, warning/block si partner name match smoke sin RNC.
4. **Auditoría:** extender `accounting-total-audit-readonly.py` con desglose B02 vs B03/B04 para FISC-01.
5. **Fix menor script C1:** corregir cálculo `without_ncf_count` en summary.

---

## Artefactos generados

| Archivo | Descripción |
|---------|-------------|
| `c1-diagnostic.json` | Payload completo del diagnóstico |
| `c1-diagnostic-raw.txt` | Log crudo odoo shell |
| `partners_affected.csv` | Tabla exportable 48 partners |
| `607_impact_breakdown.json` | Desglose B02/B03/B04 vs 607 |
| `C1_PARTNERS_RNC_DIAGNOSTIC_REPORT.md` | Este informe |

**Scripts (sin commit):**

- `scripts/c1-partners-rnc-diagnostic-test.py`
- `scripts/run-c1-partners-rnc-diagnostic-test.sh`

---

## Estado C1

**Diagnóstico completado.**  
**Corrección NO iniciada** — detenerse aquí hasta aprobación explícita para ejecutar C1 write en TEST.

Próximo paso sugerido tras aprobación: corrección por lotes (smoke → duplicados → P199 → validación 607 read-only).
