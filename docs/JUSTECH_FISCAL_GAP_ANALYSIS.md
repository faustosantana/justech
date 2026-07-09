# JUSTECH FISCAL GAP ANALYSIS

**Auditoría crítica pre-Sprint 3 — Estándar Fiscal Justech RD**

| Metadato | Valor |
|----------|-------|
| **Documento** | `JUSTECH_FISCAL_GAP_ANALYSIS.md` |
| **Versión** | 1.0.0 |
| **Fecha** | 2026-07-09 |
| **Autor** | Revisión arquitectónica externa (post Sprint 2) |
| **Rama estable** | `feature/fiscal-standard-phase3a` @ `df67dcd` (19.0.2.1.0) |
| **Proveedor de referencia** | Adel — `l10n_do_accounting` v19.0.1.0.0 (operativo en `justgroup.app` / clon dev) |
| **Alcance Justech evaluado** | Stack `justech_l10n_do_*` + acoplamientos `hellenia_*` reales en repo |
| **Principio** | **No asumir que nada está bien.** Evidencia > intención de diseño. |

---

## Resumen ejecutivo (veredicto duro)

El proyecto **no es hoy** el mejor estándar fiscal para Odoo RD. Es un **núcleo NCF prometedor en laboratorio** con arquitectura superior al proveedor, pero **operativamente inferior** porque:

1. **Adel sigue siendo el sistema que factura en producción** (~1.504 NCF históricos, 4 empresas, 15 secuencias activas).
2. **Justech fiscal no está instalado en `justech_dev` operativo** — la estabilidad real es **inferida por tests**, no demostrada con datos vivos de 4 compañías.
3. **El producto comercial declarado en el Master Plan no existe aún**: faltan `ecf`, `dgii`, `payments`, `adel_compat`, dashboard real y desacople total de `hellenia_*`.
4. **La brecha UX sigue abierta** — el proveedor gana en facturación diaria; Justech gana en arquitectura y fiscal avanzado, pero con pantallas más ruidosas.
5. **Riesgos de migración sin resolver**: índice SQL v1, backfill histórico, cutover por empresa, coexistencia imposible a largo plazo.

**Calificación honesta del estándar fiscal Justech hoy:**

| Dimensión | Nota | Comentario |
|-----------|:----:|------------|
| Arquitectura / código | **B+** | Servicios, tests, consumo auditado — bien encaminado |
| Cobertura funcional vs Adel | **C** | ~60% de ideas Adel portadas; faltan las más operativas |
| Operación real multiempresa | **D** | Validado en lab aislado, no en clon prod |
| Producto comercial desacoplado | **D-** | Reports/pagos/tesorería aún atados a Hellenia |
| Preparación e-CF / DGII online | **F** | No iniciado; solo placeholders en documentos |
| Listo para reemplazar Adel | **NO** | Falta compat, UAT cutover, backfill, índice v2 |

**Conclusión:** Sprint 1–2 construyeron **cimiento técnico**. Sprint 3+ debe cerrar **brecha funcional, migración, UX y producto** — no añadir features antes de resolver lo pendiente.

---

## 1. ¿Qué funcionalidades tiene el proveedor (Adel) que Justech todavía no posee?

Referencia: auditoría comparativa `evidence/ncf-comparison/` (2026-07-09), código Adel en servidor, Master Architecture §6.

### 1.1 Operación diaria (alta prioridad — usuario final)

| # | Funcionalidad Adel | Estado Justech | Severidad brecha |
|---|-------------------|----------------|------------------|
| 1 | **NCF oculto en borrador ventas** — usuario no ve ruido fiscal hasta postear | NCF y campos DGII visibles en formulario | **Alta** — UX ventas |
| 2 | **Taxonomía 6 tipos contribuyente** (taxpayer/nonprofit/gov/special/foreigner) con inferencia desde RNC+nombre | No existe `justech_do_taxpayer_type`; heurística mínima B01/B02 | **Alta** |
| 3 | **Matriz journal × partner → tipos permitidos** (`_get_journal_ncf_types`) | Dominio estático; sin filtro dinámico por diario+partner | **Media** |
| 4 | **Income type / expense type explícitos** en factura (columnas 606/607) | Parcial vía campos computed en reports; no UX Adel-like | **Media** |
| 5 | **Forma de pago DGII en diario** (`l10n_do_payment_form`) | No portado a `justech_l10n_do_base` | **Media** |
| 6 | **Banner warning secuencia agotándose** en factura | Campo `% consumido` en rango; sin banner en move | **Media** |
| 7 | **Cola de rangos** (queued → auto-promote al agotar) | Solo un rango activo manual; sin cola | **Alta** operación |
| 8 | **Wizards NC/ND familiares** extendiendo reversal/debit note estándar | NC/ND funcionan vía Odoo core + resolver; **sin wizards dedicados** | **Media** UX |
| 9 | **Modo simple vs modo fiscal** (dual UX) | Diseñado en docs; **no implementado** | **Alta** |
| 10 | **Propagación tipo doc desde cotización** con mínima fricción | Existe herencia SO→invoice; UX no optimizada | **Baja** |

### 1.2 Reglas de negocio DGII

| # | Regla Adel | Justech Sprint 2 | Pendiente |
|---|----------|------------------|-----------|
| 11 | B14 sin ITBIS | ✅ Implementado | — |
| 12 | RD$250k + RNC | ✅ Implementado | Excepciones régimen especial no documentadas en UI |
| 13 | B16 exportaciones bienes/servicios | ✅ Implementado | Mezcla bienes+servicios bloqueada; casos edge POS no cubiertos |
| 14 | **B11 retención 100% ITBIS compras informales** | ❌ No implementado | Requiere módulo pagos + wizard pago |
| 15 | Validación NCF B/E unificada (11/13/19 chars) en util compartido | Parcial en base validators | Parser compras E41/E31 incompleto vs Adel |
| 16 | Reglas gubernamentales / nonprofit específicas | ❌ | Sin taxpayer type no hay reglas |

### 1.3 Integración y ecosistema Adel

| # | Funcionalidad | Justech |
|---|---------------|---------|
| 17 | **Operación probada 4 empresas en producción** | Lab TransactionCase; no cutover real |
| 18 | **Integración LatAm document type** (legacy) | Justech desacoplado — **ventaja**, pero sin capa lectura histórica `adel_compat` |
| 19 | Módulo **`l10n_do_reports` Adel** (básico) | Justech reports más avanzado en diseño, **pero no desplegado operativamente** |
| 20 | **Estabilidad empírica** (1.504 NCF, cero downtime fiscal) | **Cero** NCF en justech_dev operativo con stack Justech |

### 1.4 Lo que Adel tiene y Justech **no debe** copiar (pero el proveedor “tiene” operativamente)

- Hack `_post` draft→posted — Adel lo usa; Justech correctamente no lo tiene.
- ACL permisiva en secuencias — Adel lo tiene; Justech correctamente no.

> **Veredicto §1:** Justech **aún no iguala la experiencia operativa diaria** del proveedor. La brecha no es solo código: es **funcionalidad desplegada y validada en producción**.

---

## 2. ¿Qué funcionalidades tiene Justech que el proveedor no posee?

Estas son ventajas reales — no minimizarlas — pero varias **existen solo en repo/lab**, no en operación.

### 2.1 Arquitectura y motor NCF

| # | Capacidad Justech | Adel |
|---|-------------------|------|
| 1 | **Asignación NCF pre-`_post()`** sin hack de estado | Post-post hack |
| 2 | **`justech.do.ncf.consumption`** — audit trail inmutable por consumo | Solo `ir.sequence` |
| 3 | **Locks transaccionales** (`FOR UPDATE`, `pg_advisory_xact_lock`) | Sin lock de fila |
| 4 | **Duplicados v2.0 Python** (venta vs compra por emisor) | Unicidad plana / lógica duplicada en move |
| 5 | **Capa services/validators/providers** desacoplada | Monolito ~2.249 LOC |
| 6 | **37+ tests automatizados NCF** (lab) | **0 tests** |
| 7 | **Centro de Administración Fiscal** | No existe equivalente |
| 8 | **Diagnóstico fiscal read-only** automatizado | No existe |
| 9 | **Anulación NCF formal** (void reason, manager ACL) | Limitado / distinto modelo |
| 10 | **Record rules fiscales** por rol | ACL abierta en secuencias |

### 2.2 Reportes y workflow DGII (diseño Justech reports)

| # | Capacidad | Adel |
|---|-----------|------|
| 11 | Workflow revisión → exclusión → aprobación → export | Export directo |
| 12 | Bandeja pendientes supervisor | No |
| 13 | Historial export con hash | No |
| 14 | Wizard blocker pre-export | No |
| 15 | Tests extensos 606/607/608 (~30+) | No |

### 2.3 Producto y gobernanza (visión, no operación)

| # | Capacidad | Adel |
|---|-----------|------|
| 16 | Registro `justech_register` / catálogo comercial | No |
| 17 | SemVer Odoo + CHANGELOG/MIGRATION por módulo | No |
| 18 | Anti-hardcode checker (`tools/fiscal_no_hardcode_check.py`) | Hardcodes operativos |
| 19 | Master Plan desacoplado multi-cliente | Acoplado fork LatAm |
| 20 | Preparación JAIOS / eventos read-only (diseño) | No |

> **Veredicto §2:** Justech **supera claramente** al proveedor en arquitectura, seguridad, trazabilidad y workflow DGII **en papel**. En **justgroup.app hoy**, esas ventajas **valen cero** porque no están instaladas.

---

## 3. ¿Qué funcionalidades deberían eliminarse del diseño actual?

Auditoría sin piedad sobre decisiones que generan deuda o confusión.

| # | Elemento | Por qué eliminar o congelar | Acción recomendada |
|---|--------|----------------------------|-------------------|
| 1 | **`justech_l10n_do_reports_hellenia`** como puente permanente | Viola P2 producto comercial; duplica responsabilidades | **Eliminar del producto estándar**; mantener solo migración temporal |
| 2 | **Dependencia reports → `hellenia_account`** (Python withholding) | Rompe portabilidad; bloquea cliente #2 | **Eliminar referencia**; adapter a `justech_l10n_do_payments` |
| 3 | **Índice SQL v1** `(company_id, justech_do_ncf)` | Falsos positivos; bloquea casos fiscales válidos | **Reemplazar** (plan v2.0) — no mantener indefinidamente |
| 4 | **Campos DGII duplicados** en move (status, exclusion, fiscal_state, cancel_type…) sin UX unificada | Ruido visual; confunde usuarios ventas | **Consolidar** en pestaña + modo fiscal; ocultar en modo simple |
| 5 | **`justech_l10n_do_payments_withholding` vacío** (solo catálogo XML) | Falsa sensación de módulo entregado | Renombrar a `_stub` o documentar como **no-módulo** hasta migración |
| 6 | **Dashboard shell** como `application: True` | Menú vacío = deuda UX | Ocultar hasta Sprint 4 o degradar a `application: False` |
| 7 | **Duplicación report stacks** (`hellenia_reports` + `justech_report_design`) | Overrides conflictivos | Elegir **una** pila; deprecar la otra |
| 8 | **Referencias `hellenia.cloud` en manifests** producto Justech | Inconsistente con P2 comercial | Cambiar a `justech.do` en todo stack fiscal |
| 9 | **ROADMAP.md desactualizado** en ncf (Sprint 2 marca pendiente lo ya hecho) | Desinforma al equipo | Actualizar o eliminar duplicados vs Master Plan |
| 10 | **Coexistencia Adel + Justech** como estrategia permanente | Dos motores `_post` = bomba de tiempo | **Prohibir** — solo ventana migración con `adel_compat` |

---

## 4. ¿Qué funcionalidades deberían rediseñarse completamente?

No parches — rediseño estructural obligatorio.

| # | Área | Problema actual | Rediseño requerido |
|---|------|-----------------|-------------------|
| 1 | **Migración Adel → Justech** | No existe `justech_l10n_do_adel_compat`; desinstalar Adel destruye columnas | Módulo temporal: backfill read-only, snapshot legacy, wizard cutover por empresa |
| 2 | **Clave fiscal duplicados** | Python v2.0 vs SQL v1 — **dos verdades** | Un solo contrato: validators + índices parciales + `account_move.init()` alineados |
| 3 | **UX factura** | 10+ campos fiscales visibles | Dual mode: Simple (2 campos) / Fiscal (pestaña completa); NCF readonly post |
| 4 | **Tipo contribuyente + tipo comprobante** | Heurística mínima partner | Modelo `justech.do.taxpayer.type` + reglas declarativas + tests matriz |
| 5 | **Retenciones y 623** | Lógica en `hellenia_account`; reports acoplado | `justech_l10n_do_payments` como **único dueño**; reports solo adapter |
| 6 | **Multiempresa** | Tests crean compañías sin COA completo; `continue` si no hay income account | Fixture enterprise multi-COA o chart template DO por compañía en tests + UAT 4 empresas reales |
| 7 | **POS fiscal** | Diseño Phase 29; no integrado al stack NCF Sprint 2 | Bridge POS → resolver NCF → consumo; no duplicar secuencias POS |
| 8 | **Serie E / prefijos E31–E34** | Tratados como NCF B en tests parciales | Separar dominio: NCF tradicional vs e-CF staging tables |
| 9 | **Exportadores DGII** | XLSX/CSV custom; **sin TXT oficial DGII** | Capa `adapters/dgii_format_official.py` con golden files por formato |
| 10 | **Diagnóstico vs Dashboard** | Diagnóstico en ncf; dashboard vacío | Fusionar: dashboard consume diagnostic + audit services |

---

## 5. ¿Qué funcionalidades nuevas incorporará el estándar Justech que hoy ninguno de los dos tiene?

Estas son la **propuesta de valor** del estándar — casi ninguna está implementada aún.

| # | Funcionalidad nueva | Beneficio | Estado |
|---|---------------------|-----------|--------|
| 1 | **Centro de Salud Fiscal** (semáforo integridad ERP) | Visión única 606/607/NCF/pagos | Diseño only |
| 2 | **Diagnóstico automatizado pre-cierre** | Reduce errores DGII | ✅ Sprint 2 (read-only) |
| 3 | **Duplicados fiscales v2.0 con explicación** (“colisiona con FAC-xxx proveedor Y”) | Menos falsos positivos | Parcial — mensajes mejorables |
| 4 | **Wizard configuración fiscal 15 min** (empresa nueva) | Onboarding comercial | ❌ |
| 5 | **API read-only JAIOS** (consumo, rangos, diagnóstico) | IA / observabilidad | ❌ |
| 6 | **Event bus fiscal** (`ncf.consumed`, `ncf.voided`, `dgii.exported`) | Integraciones | ❌ |
| 7 | **Feature flags por empresa** (`justech_do_fiscal_mode`) | Cutover gradual | Campo parcial en company |
| 8 | **Hash y auditoría de exports DGII** | Compliance | ✅ en reports |
| 9 | **Modo paralelo migración** (Adel read + Justech write new) | Riesgo cero histórico | ❌ |
| 10 | **Certificación marketplace Justech** (módulos licenciables desacoplados) | Revenue | Catálogo parcial |
| 11 | **Validación RNC online DGII** (async) | Calidad datos | ❌ módulo dgii stub |
| 12 | **Conciliación fiscal pago↔retención↔623** | Cierre integrado | ❌ |
| 13 | **POS mixed fiscal** (efectivo + tarjeta + NCF) | Retail RD | Diseño Phase 29 only |
| 14 | **Observabilidad** (métricas NCF/día, rangos %, errores post) | Ops enterprise | ❌ |

> **Veredicto §5:** El estándar **promete** más que Adel y más que Odoo base, pero **~85% de la propuesta diferenciadora sigue en documentos**, no en código desplegable.

---

## 6. ¿Qué riesgos quedan pendientes?

| ID | Riesgo | Prob. | Impacto | Evidencia | Mitigación pendiente |
|----|--------|:-----:|:-------:|-----------|---------------------|
| R1 | **Cutover Adel→Justech sin backfill** destruye 1.504 NCF metadata | Media | **Crítico** | Fase 2 lab learnings | `adel_compat` + UAT |
| R2 | **Índice SQL v1** bloquea migración compra/venta mismo string | Alta | Alto | NCF audit v2.0 | Aprobar y aplicar v2.0 en lab |
| R3 | **Dos motores `_post`** si coexistencia prolongada | Media | **Crítico** | Master Plan P3 | Ventana migración acotada |
| R4 | **Justech no probado en datos reales 4 empresas** | Alta | Alto | justech_dev sin Justech | Clon prod → install → smoke |
| R5 | **UX inferior → usuarios sabotearán campos fiscales** | Alta | Medio | UX audit Adel 8.0 vs 6.5 | Dual mode Sprint 3–4 |
| R6 | **Reports acoplado hellenia_account** | Alta | Alto | Enterprise cert | Desacople payments |
| R7 | **623 incorrecto sin pagos Justech** | Media | Alto | F623 docs | Migrar retenciones |
| R8 | **Concurrencia NCF en POS** no validada | Media | Alto | Phase 29 gap | Tests carga POS |
| R9 | **e-CF obligatorio DGII futuro** sin módulo | Alta | **Crítico** long-term | eNCF calificación F | Roadmap ecf |
| R10 | **Despliegue prod sin aprobación explícita** | Baja | **Crítico** | Directiva Maestra | Gate formal |
| R11 | **Falsos duplicados en auditoría** confunden decisión | Media | Medio | 9/10 FP v2.0 | Comunicación + UI |
| R12 | **Cron expiración rangos** ausente — post bloqueado sorpresa | Media | Medio | FINAL_FISCAL_REVIEW | Cron + alertas |

---

## 7. ¿Qué deuda técnica queda pendiente?

| # | Deuda | Ubicación | Prioridad |
|---|-------|-----------|-----------|
| 1 | Índice único SQL v1 vs lógica Python v2.0 | `account_move.init()` | **P0** |
| 2 | Módulo `adel_compat` inexistente | — | **P0** migración |
| 3 | `hellenia_account` dentro cadena reports/623 | reports Python | **P0** producto |
| 4 | ROADMAP ncf desincronizado | `ROADMAP.md` | P2 |
| 5 | Providers/adapters en base — **stubs vacíos** | `justech_l10n_do_base` | P1 |
| 6 | Dashboard application vacío | dashboard | P2 |
| 7 | payments_withholding — shell comercial | manifest | P1 |
| 8 | Treasury depende hellenia wizard | treasury | P2 |
| 9 | Tests multiempresa omiten post si falta COA | test_ncf_sprint2_part2 | P1 |
| 10 | Website manifests mixtos hellenia/justech | varios `__manifest__.py` | P3 |
| 11 | Sin CI pipeline fiscal en GitHub | repo | P1 |
| 12 | SQL crudo en `consume_next` sin abstraction | ncf_range.py | P2 |
| 13 | Campos DGII en move sin consolidación UX | account_move views | P1 |
| 14 | B11/B13 reglas incompletas | ncf validators | P1 |
| 15 | Export TXT oficial DGII ausente | reports | P1 |
| 16 | Sin golden files regression DGII | tests | P2 |

---

## 8. ¿Qué componentes todavía no cumplen el estándar Enterprise?

Criterios Enterprise (Master Plan + ERP Enterprise Certification):

| Componente | Cumple | Brecha |
|------------|:------:|--------|
| Capa services/validators | ⚠️ | base providers vacíos; ncf avanzado |
| Tests automatizados | ⚠️ | Solo lab; reports no en pipeline unificado |
| Seguridad ACL/record rules | ✅ | ncf bien; reports parcial |
| Documentación SemVer | ⚠️ | ROADMAP stale; manifests mixtos |
| Zero hardcode | ⚠️ | Checker existe; no enforced en CI |
| Desacople cliente | ❌ | hellenia_* en cadena crítica |
| Observabilidad | ❌ | Sin métricas/logs fiscal |
| Multi-tenant / multi-cliente | ❌ | Producto no instalable standalone |
| Rollback documentado | ⚠️ | MIGRATION ncf sí; cutover Adel no |
| UX Enterprise | ❌ | Dual mode ausente |
| API externa controlada | ❌ | JAIOS stub |
| Certificación go-live | ❌ | Score 79/100 — NO ERP Ready |

**Componentes más lejos del estándar:**

1. `justech_l10n_do_payments` (no existe como código)
2. `justech_l10n_do_ecf` / `justech_l10n_do_dgii` (no existen)
3. `justech_l10n_do_adel_compat` (no existe)
4. `justech_l10n_do_dashboard` (shell)
5. Cadena `hellenia_account` → reports → treasury

---

## 9. ¿Qué módulos están listos para producción?

Criterio estricto: **instalable en cliente nuevo RD sin Adel, con UAT completo y rollback probado**.

| Módulo | Versión | Prod-ready | Notas críticas |
|--------|---------|:----------:|----------------|
| **Adel `l10n_do_accounting`** | 19.0.1.0.0 | ✅ **Hoy en prod** | Base operativa actual — no es Justech |
| `justech_l10n_do_base` | 19.0.1.6.0 | ⚠️ **Condicionado** | Tests base OK; providers stub; no UAT prod |
| `justech_l10n_do_ncf` | 19.0.2.1.0 | ⚠️ **Solo lab** | 37 tests lab; **no** en justech_dev operativo |
| `justech_l10n_do_reports` | 19.0.1.14.0 | ⚠️ **Condicionado** | Tests sólidos; acoplamiento hellenia; no cutover |
| `justech_l10n_do_dashboard` | 19.0.1.0.0 | ❌ | Shell vacío |
| `justech_l10n_do_payments_withholding` | 19.0.1.0.0 | ❌ | Catálogo only |
| `justech_l10n_do_treasury` | 19.0.1.2.0 | ⚠️ | UX; depende hellenia; no fiscal core |
| `hellenia_account` | — | ✅ **Prod piloto** | Retenciones reales; **no es producto Justech puro** |
| `hellenia_ux` | — | ⚠️ | Overrides fiscales cliente |
| POS fiscal | — | ❌ | Incomplete SKU |

**Respuesta directa:** **Ningún módulo del stack Justech fiscal está listo para reemplazar Adel en producción.**  
Lo más cercano: **`justech_l10n_do_ncf` en lab** como candidato a piloto **después** de compat + UAT clon.

---

## 10. ¿Qué módulos todavía están en desarrollo?

| Módulo | Fase | % estimado | Bloqueador |
|--------|------|:----------:|------------|
| `justech_l10n_do_ncf` | Sprint 2 ✅ | **~70%** | Índice v2, B11, wizards, UX, adel_compat |
| `justech_l10n_do_base` | Sprint 1 ✅ | **~55%** | Taxpayer types, payment form journal, adapters DGII |
| `justech_l10n_do_reports` | Phase 19–21 | **~75%** | 609, TXT oficial, desacople hellenia |
| `justech_l10n_do_dashboard` | Sprint 1 shell | **~15%** | Widgets, KPIs, alertas |
| `justech_l10n_do_payments` | Diseño | **~5%** | Migración desde hellenia_account |
| `justech_l10n_do_ecf` | — | **0%** | No creado |
| `justech_l10n_do_dgii` | — | **0%** | No creado |
| `justech_l10n_do_adel_compat` | — | **0%** | **Bloqueante migración** |
| POS fiscal (`hellenia_pos` + diseño 29) | Diseño/UAT | **~40%** | Integración NCF Justech |
| `justech_l10n_do_treasury` | UX | **~60%** | No fiscal; acoplado hellenia |

---

## 11. ¿Qué pruebas faltan para considerar terminado el estándar fiscal?

Checklist **mínimo** antes de declarar “estándar fiscal completo” (no Sprint 3 — **producto**):

### 11.1 Pruebas automatizadas faltantes

- [ ] Índice SQL v2.0 — tests migración up/down
- [ ] B11 informal withholding — unit + integration con pagos
- [ ] Taxpayer type matrix — todas las combinaciones journal×partner
- [ ] Parser NCF E-series y longitudes 11/13/19
- [ ] Golden file exports **TXT oficial** 606/607/608/623
- [ ] Formato **609** completo
- [ ] Concurrencia NCF — stress 10+ usuarios simultáneos
- [ ] POS mixed fiscal E2E
- [ ] Multiempresa — 4 compañías con COA real (no `continue`)
- [ ] `adel_compat` backfill — 1.504 registros sin `_post`
- [ ] Regression suite unificada CI (`base + ncf + reports + payments`)

### 11.2 UAT / validación humana faltante

- [ ] Cutover empresa 1 en clon prod (solo lab clon)
- [ ] Ciclo completo venta→pago→retención→623→606/607
- [ ] NC/ND wizards usuario contador + usuario ventas
- [ ] Cierre mes DGII con workflow aprobación
- [ ] Rollback documentado ejecutado en lab
- [ ] Comparativa side-by-side Adel vs Justech (mismos documentos)
- [ ] Manual usuario producto Justech (no Hellenia)
- [ ] Sign-off propietario explícito pre-prod

### 11.3 Umbrales numéricos objetivo

| Métrica | Hoy | Objetivo estándar |
|---------|-----|-------------------|
| Tests NCF | 37 (lab) | 80+ incl. integración |
| Tests reports | ~30 | 50+ con golden TXT |
| Cobertura servicios fiscales | ~60% estimado | ≥80% |
| UAT empresas reales | 0 Justech | 4/4 cutover clon |
| Falsos duplicados auditoría | Resuelto en v2.0 Python | 0 con SQL alineado |

---

## 12. ¿Qué funcionalidades pasarán a e-CF y cuáles permanecerán exclusivamente en NCF?

### 12.1 Permanecen en **NCF tradicional** (`justech_l10n_do_ncf`)

Serie **B** y comprobantes **físicos / pre-e-CF**:

| Prefijo | Función | Notas |
|---------|---------|-------|
| B01 | Crédito fiscal | Core NCF |
| B02 | Consumo final | Core NCF |
| B03 | Nota débito | Core NCF |
| B04 | Nota crédito | Core NCF |
| B11 | Compras | Validación NCF proveedor |
| B12 | Regímenes especiales | |
| B13 | Gastos menores | |
| B14 | Régimen especial sin ITBIS | Reglas Sprint 2 |
| B15 | Gubernamental | |
| B16 | Exportaciones | Reglas Sprint 2 |
| B17 | Pagos al exterior (compras) | Parcial |

**Responsabilidades NCF permanentes:**

- Rangos y consumo serie B
- Asignación pre-post tradicional
- Void/anulación 608 (NCF papel)
- Duplicados clave fiscal v2.0
- Diagnóstico rangos
- Integración POS **serie B** mientras DGII lo permita

### 12.2 Migran a **e-CF** (`justech_l10n_do_ecf` — futuro)

Serie **E** y comprobantes electrónicos:

| Prefijo | Función |
|---------|---------|
| E31 | Crédito fiscal electrónico |
| E32 | Consumo electrónico |
| E33 | Notas electrónicas |
| E34 | Compras electrónicas |
| E41+ | Compras/gastos electrónicos proveedor |

**Responsabilidades e-CF (no en ncf core):**

- Generación XML DGII
- Firma digital / certificado
- Envío y acuse DGII (Web Services)
- QR en PDF / representación impresa
- Estado documento (aceptado/rechazado/condicional)
- Contingencia / modo offline
- Integración proveedor certificado (Infile, etc.)
- Re-envío, anulación electrónica
- TrackId, código seguridad, fecha firma

### 12.3 Compartido (bridge, no duplicar)

| Concern | Dueño | Mecanismo |
|---------|-------|-----------|
| Tipo comprobante catálogo | `base` | Un registro; flag `is_electronic` |
| Partner fiscal / RNC | `base` | Compartido |
| Reglas RD$250k, export | `ncf` validators | e-CF **reutiliza** validators |
| Reportes 606/607 | `reports` | Columnas distintas E vs B; mismo workflow |
| Anulaciones 608 | `reports` + void NCF | e-CF añade estado DGII |
| Secuencias | **Separadas** | NCF range ≠ e-CF folio DGII |

### 12.4 Regla arquitectónica (Master Plan)

```
justech_l10n_do_ncf     → NO importa ecf
justech_l10n_do_ecf     → depende de ncf (hooks post-consumo)
justech_l10n_do_dgii    → adapters HTTP (RNC, validación) — usado por ambos
```

**Riesgo si no se respeta:** duplicar lógica E31 como “otro NCF” dentro de `ncf` — **prohibido**.

### 12.5 Estado actual honesto

| Capacidad | NCF B | e-CF E |
|-----------|:-----:|:------:|
| Rangos/consumo | ✅ | ❌ |
| Asignación auto | ✅ B01–B17 parcial | ❌ |
| Reglas negocio | ⚠️ parcial | ❌ |
| Reportes DGII | ✅ 606/607/608 | ❌ E-specific |
| XML/QR/WS | ❌ | ❌ |
| Histórico E31 en prod (587 docs Adel) | Metadato legacy | Requiere bridge lectura |

---

## Matriz resumen: Adel vs Justech vs Estándar objetivo

| Capacidad | Adel hoy | Justech hoy | Estándar Justech |
|-----------|:--------:|:-----------:|:----------------:|
| Operación prod | ✅ | ❌ | ✅ |
| Arquitectura | ⚠️ | ✅ | ✅ |
| UX ventas | ✅ | ❌ | ✅ |
| UX fiscal | ⚠️ | ✅ | ✅ |
| Tests | ❌ | ⚠️ lab | ✅ CI |
| 606/607/608 | ⚠️ | ⚠️ | ✅ |
| 623/retenciones | ⚠️ hellenia | ⚠️ hellenia | ✅ payments |
| 609/IT-1 | ❌ | ❌ | ✅ v2 |
| e-CF | ⚠️ E31 prod | ❌ | ✅ ecf module |
| Migración Adel | N/A | ❌ | ✅ compat |
| Producto multi-cliente | ❌ | ❌ | ✅ |

---

## Recomendación pre-Sprint 3 (orden obligatorio)

**No iniciar features nuevas hasta:**

1. **Crear `justech_l10n_do_adel_compat`** — backfill + lectura legacy (P0).
2. **Aprobar/aplicar índice SQL v2.0 en lab** — alinear con Python (P0).
3. **Desacoplar reports de `hellenia_account`** — adapter payments stub (P0).
4. **Implementar dual UX** — modo simple ventas (P1).
5. **UAT clon 4 empresas** — instalar Justech stack completo (P0).
6. **Taxonomía taxpayer + B11** — cerrar reglas Adel restantes (P1).
7. **Solo entonces:** dashboard widgets, ecf stub, dgii RNC online.

---

## Referencias

| Documento | Ruta |
|-----------|------|
| Master Plan | `docs/JUSTECH_FISCAL_MASTER_PLAN.md` |
| Comparativa Adel | `evidence/ncf-comparison/NCF_COMPARATIVE_EVALUATION.md` |
| Sprint 2 Report | `evidence/fiscal-phase3/SPRINT2_REPORT.md` |
| Índice SQL v2.0 plan | `evidence/fiscal-phase3/NCF_INDEX_V2_PLAN.md` |
| Enterprise Certification | `docs/ERP_JUSTECH_ENTERPRISE_CERTIFICATION.md` |
| NCF Master Architecture | `evidence/ncf-comparison/JUSTECH_NCF_MASTER_ARCHITECTURE.md` |

---

## Control de cambios

| Versión | Fecha | Autor | Cambio |
|---------|-------|-------|--------|
| 1.0.0 | 2026-07-09 | Auditoría pre-Sprint 3 | Emisión inicial post 19.0.2.1.0 |

---

*Este documento es deliberadamente crítico. Su propósito es impedir complacencia antes del Sprint 3.*  
*No autoriza despliegue en producción, merge a development/main, ni aplicación del índice SQL v2.0.*
