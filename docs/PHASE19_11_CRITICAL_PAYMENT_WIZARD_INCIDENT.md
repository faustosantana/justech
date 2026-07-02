# Fase 19.11 — Incidente crítico wizard pagos (PROD)

**Fecha:** 2026-07-01  
**Estado:** PROD **FAIL** — rollback ejecutado; hotfix **no desplegado** (pendiente autorización)

---

## Resumen ejecutivo

El usuario reportó que el wizard **Clientes → Pagos → Nuevo** seguía pagando **todas** las facturas aunque solo una fuera seleccionada. Los PASS de Fase 19.7 y 19.9 quedan **invalidados** (validación solo por shell, sin navegador).

Se ejecutó rollback de PROD al backup `2026-07-01_1156` (el script estándar falló; se completó con `DROP DATABASE` + restauración parcial del dump).

---

## ROLLBACK

| Campo | Valor |
|-------|-------|
| **Ejecutado** | **Sí** |
| **Backup destino** | `backups/hellenia-prod/2026-07-01_1156` |
| **Motivo fallo inicial** | `restore-hellenia-prod.sh` inyecta dump cluster completo sin `DROP DATABASE` → miles de errores `already exists`, BD sin cambios |
| **Corrección aplicada** | `DROP DATABASE hellenia_prod` + extracción sección `hellenia_prod` del dump + filestore + custom.tar.gz |
| **Backup seguridad pre-restore** | `2026-07-01_1221` (estado con v25 y 7 pagos erróneos) |
| **Módulo post-rollback** | `hellenia_account` **19.0.1.0.23** |
| **Pagos PBNKD eliminados por rollback** | `00005`, `00006`, `00007` y estado posterior a 11:56 |
| **Pagos PBNKD que persisten (del propio backup 1156)** | `00001`–`00004` @ RD$11,800 c/u (creados 11:44–11:46) |

> **Nota:** El backup 1156 **ya contenía** pagos incorrectos de pruebas previas. Un punto más limpio sería `2026-07-01_1131` (sin PBNKD/2026, módulo v21).

---

## Causa raíz real

### 1. Bug servidor — carga inicial incorrecta

En `_load_pending_invoices()` (versiones desplegadas v23–v25 en servidores):

```python
"apply": False,
"amount_to_pay": abs(move.amount_residual),  # ← INCORRECTO
```

El fix documentado en Fase 19.9 (`amount_to_pay: 0.0`) **existe en el repositorio workspace** pero **nunca se desplegó** a TEST ni PROD (verificado en contenedores y disco VPS).

### 2. Bug UI — todas las facturas aparecen marcadas

**Reproducido con Playwright** en TEST (`hellenia_test`, v25):

- Cliente `SMOKE P13.4 CF`, 3 facturas pendientes
- Al seleccionar cliente: **`checked=3, total=3`** (todas marcadas)
- Total wizard: **RD$30,400** (suma de todos los residuales)
- Captura: `evidence/phase19-11/screenshots-test/05-apply-checkboxes-on-load.png`

En ORM inmediatamente después de `create()`: `apply=False` pero `amount_to_pay=residual` en cada línea. La UI de Odoo 19 (lista editable + `force_save` en `apply`/`amount_to_pay`) **muestra y trata las filas como seleccionadas** cuando `amount_to_pay` viene precargado con el residual.

### 3. Registro paga todas las seleccionadas visuales

`action_register_payments()` itera `_selected_lines()` filtradas por `apply=True`. Tras el guardado implícito del formulario al pulsar **Registrar pago**, el payload UI persiste `apply=True` en todas las filas → se crean N pagos por el residual completo (RD$11,800).

### 4. PASS falsos anteriores

Los scripts Fase 19.7/19.9 usaban `wizard.write()` con una sola línea `apply=True`, **sin simular** el comportamiento del listado editable ni abrir el wizard en navegador.

---

## Vista y método en PROD (post-rollback v23)

| Elemento | Valor |
|----------|-------|
| **Vista** | `hellenia.payment.partner.wizard.form` (ir.ui.view id **1730**) |
| **Campo apply** | `<field name="apply" force_save="1"/>` |
| **Campo amount_to_pay** | `force_save="1"`, `readonly="not apply"` (en v25; v23 similar sin guards SQL) |
| **Acción menú Nuevo** | `hellenia_account.action_hellenia_register_customer_payment` → modelo `hellenia.payment.partner.wizard` |
| **Botón** | `action_register_payments` (type=object) en footer del form |
| **hellenia_ux** | **uninstalled** — no hay wizard alternativo |

---

## Evidencia UI

| Entorno | Resultado | Evidencia |
|---------|-----------|-----------|
| **PROD** (`odoo.hellenia.cloud`) | Login UI **no disponible** (credencial `CertFiscal20!` rechazada para `it@justech.do`) | `evidence/phase19-11/screenshots/00-login-fail.png` |
| **TEST** (`test.hellenia.cloud`) | **Bug reproducido** — 3/3 checkboxes marcados al cargar | `evidence/phase19-11/screenshots-test/05-apply-checkboxes-on-load.png` |

---

## Pagos incorrectos

### Eliminados por rollback (estado 12:16–12:19, ya no en PROD)

| Pago | Monto | Fecha | Usuario |
|------|-------|-------|---------|
| PBNKD/2026/00001–00007 (sesión 12:16–12:19) | RD$11,800 c/u | 2026-07-01 12:16–12:19 | it@justech.do |

### Persisten en PROD post-rollback (del backup 1156)

| Pago | Monto | Factura vinculada | Impacto |
|------|-------|-------------------|---------|
| PBNKD/2026/00001 | RD$11,800 | INV/2026/00003 | Factura marcada paid |
| PBNKD/2026/00002 | RD$11,800 | INV/2026/00004 | Factura marcada paid |
| PBNKD/2026/00003 | RD$11,800 | INV/2026/00004 (diag) | Factura marcada paid |
| PBNKD/2026/00004 | RD$11,800 | INV/2026/00001 | Factura marcada paid |

**Cliente afectado:** SMOKE P13.4 CF  
**Factura aún abierta post-rollback:** INV/2026/00002 (RD$11,800 not_paid)

### Acciones de limpieza recomendadas (requieren autorización)

1. **No borrar** pagos sin aprobación contable.
2. Para cada pago incorrecto: evaluar **cancelar** (`button_cancel`) o **borrador + unlink** según política Hellenia.
3. Reabrir facturas afectadas si el pago se revierte (`payment_state` → `not_paid`).
4. Conciliar diario BNKD y secuencia PBNKD/2026.
5. Considerar rollback adicional a `2026-07-01_1131` si se requiere estado sin ningún PBNKD/2026.

---

## Impacto contable

- Pagos duplicados/incorrectos por RD$11,800 en cliente de prueba **SMOKE P13.4 CF**.
- Riesgo de replicarse en clientes reales si se usa el wizard sin fix.
- **Mitigación inmediata:** PROD en v23 (pre-v25); wizard sigue con bug de `amount_to_pay=residual` — **usar con extrema precaución** o deshabilitar botón Nuevo hasta hotfix certificado.

---

## Próximos pasos (no ejecutados en 19.11)

1. Hotfix mínimo: `amount_to_pay=0`, guard servidor con SQL, error si todas `apply=True` sin confirmación.
2. Desplegar solo tras Playwright PASS en TEST y PROD con credenciales válidas.
3. Reparar `restore-hellenia-prod.sh` para hacer `DROP DATABASE` antes de restaurar.

---

## Veredicto

| Criterio | Resultado |
|----------|-----------|
| **PROD PASS / FAIL** | **FAIL** |
| **Rollback** | **Sí** (completado manualmente) |
| **Causa raíz confirmada en UI** | **Sí** (TEST Playwright) |
| **PASS 19.7 / 19.9** | **INVÁLIDOS** |
