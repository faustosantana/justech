# Fase 3 — Checklist de configuración funcional (empresa Hellenia)

**Cliente:** Hellenia, S.R.L. — República Dominicana  
**Ambiente:** `hellenia_dev` — https://dev.hellenia.cloud  
**Base de datos:** `hellenia_dev`  
**Fecha:** 2026-06-30  
**Versión:** 1.0  
**Estado:** **Borrador para aprobación** — sin cambios aplicados en DEV

---

## Propósito

Parametrizar la empresa Hellenia en DEV como **base funcional** para las fases siguientes (localización RD, ventas, compras, inventario, POS, contabilidad, reportes).

Este documento consolida valores propuestos, fuentes documentales, estado actual en DEV y datos pendientes de confirmar por Hellenia **antes** de ejecutar cambios.

---

## Restricciones (aprobación cliente)

| Restricción | Aplica |
|-------------|--------|
| No crear usuarios operativos | ✅ |
| No tocar TEST | ✅ |
| No tocar PRODUCCIÓN | ✅ |
| No desarrollar módulos custom | ✅ |
| No modificar core / `enterprise/` | ✅ |
| No instalar módulos de terceros | ✅ |
| No continuar TC-003 en esta fase | ✅ |

---

## Estado actual en DEV (línea base)

Evidencia: [TC-002-RESULT.md](TC-002-RESULT.md), `evidence/l10n-do-tests/2026-06-30/TC-002/`

| Elemento | Valor actual en BD | Nota |
|----------|-------------------|------|
| Nombre empresa | **Hellenia Pruebas RD** | Empresa de laboratorio TC-002 — **reemplazar por datos legales** |
| País | República Dominicana (`DO`) | ✅ Correcto |
| Moneda compañía | DOP | ✅ Correcto |
| RNC (`vat`) | `131793916` | **Ficticio de prueba** — no es el RNC documentado oficial |
| Dirección | Av. Winston Churchill 123, Santo Domingo 10101 | **Ficticia de prueba** |
| Teléfono | +1 809-555-0100 | **Ficticio de prueba** |
| Correo | *(vacío o no documentado)* | Pendiente |
| Plan contable | `do` cargado — 288 cuentas | ✅ Ya aplicado |
| Impuestos ITBIS | 14 + retenciones | ✅ Cargados por `l10n_do` |
| Diarios | 7 (ver §10) | ✅ Precargados por localización |
| Usuarios | Solo `admin` | ✅ Sin usuarios nuevos |
| `l10n_do` / `l10n_do_reports` | Instalados (TC-001) | No reinstalar en Fase 3 |

**Acción Fase 3:** Actualizar ficha empresa y maestros transversales **sin** deshacer plan contable ni localización ya cargada, salvo que Hellenia apruebe reset controlado.

---

## Fuentes documentales usadas

| Fuente | Dato utilizado |
|--------|----------------|
| [PROJECT_STRATEGY.md](PROJECT_STRATEGY.md) | Plataforma Odoo 19 EE on-premise; Fase 3 en curso |
| [IMPLEMENTATION_MASTER_PLAN.md](IMPLEMENTATION_MASTER_PLAN.md) | Parámetros empresa, maestros, justificación |
| [ENTERPRISE_ANALYSIS.md](ENTERPRISE_ANALYSIS.md) | Hellenia, S.R.L. — mobiliario y decoración (retail/distribución) |
| [INFILE-REQUIREMENTS.md](INFILE-REQUIREMENTS.md) | RNC `133621282` (referencia fiscal Hellenia) |
| [L10N_DO_TEST_PLAN.md](L10N_DO_TEST_PLAN.md) | TC-005/006 — campos empresa RD; RNC ejemplo `133621282` |
| [TC-002-RESULT.md](TC-002-RESULT.md) | Estado actual DEV y datos de prueba |
| [NCF_IMPLEMENTATION.md](NCF_IMPLEMENTATION.md) | Requisitos fiscales empresa emisora |
| Suscripción Odoo | `M260616306091776` |

---

## Checklist detallado

### 1. Datos legales de la empresa

| # | Campo Odoo | Valor propuesto | Fuente / nota | Estado | Acción en DEV (post-aprobación) |
|---|------------|-----------------|---------------|--------|--------------------------------|
| 1.1 | Razón social (`res.company.name`) | **Hellenia, S.R.L.** | Cliente documentado en todo el proyecto | ☐ Confirmar | Ajustes → Empresas → nombre legal |
| 1.2 | Nombre comercial (si distinto) | **Hellenia** | Uso habitual marca | ☐ Confirmar | Campo nombre comercial / partner si aplica |
| 1.3 | Forma jurídica | S.R.L. | Documentación proyecto | ☐ Confirmar | Solo documental; no campo obligatorio Odoo |
| 1.4 | Rubro / actividad | Mobiliario y decoración — retail/distribución | [ENTERPRISE_ANALYSIS.md](ENTERPRISE_ANALYSIS.md) | ☐ Confirmar | Notas internas; actividad económica DGII si existe campo |
| 1.5 | Logo | *(pendiente archivo)* | Identidad en facturas/POS | ☐ Pendiente | Subir imagen en ficha empresa |
| 1.6 | Sitio web | `https://hellenia.cloud` | Manifests custom / docs proyecto | ☐ Confirmar | Campo `website` en empresa/contacto |
| 1.7 | Idioma documentos | Español (`es_DO` / `es`) | [IMPLEMENTATION_MASTER_PLAN.md](IMPLEMENTATION_MASTER_PLAN.md) | ☐ Confirmar | Ajustes → Traducciones; idioma compañía |
| 1.8 | Suscripción Odoo (referencia) | `M260616306091776` | [E1B-LICENSE-CHECKLIST.md](E1B-LICENSE-CHECKLIST.md) | ℹ️ Info | Registro licencia diferido a go-live |

**Criterio de aceptación:** Razón social legal visible en Ajustes → Empresas y en vista previa de documentos.

---

### 2. RNC

| # | Campo | Valor propuesto | Fuente | Estado | Nota consultor |
|---|-------|-----------------|--------|--------|----------------|
| 2.1 | RNC empresa (`vat` en `res.partner` de compañía) | **133621282** | [INFILE-REQUIREMENTS.md](INFILE-REQUIREMENTS.md), TC-006 plan | ☐ **Confirmar con Hellenia** | Dato distinto al ficticio TC-002 (`131793916`) |
| 2.2 | Formato | 9 dígitos sin guiones | Convención DGII | ☐ Confirmar | Validar dígito verificador si aplica |
| 2.3 | Visible en factura / PDF | Sí | Requisito fiscal RD | ☐ Validar post-config | Tras TC-030 o preview factura |

**Decisión requerida:** Confirmar si `133621282` es el RNC vigente de Hellenia, S.R.L. para DEV y futuro go-live.

---

### 3. Dirección fiscal

| # | Campo | Valor propuesto | Estado actual DEV | Estado |
|---|-------|-----------------|-------------------|--------|
| 3.1 | Calle y número | *(pendiente dato oficial)* | Av. Winston Churchill 123 *(ficticio)* | ☐ Confirmar |
| 3.2 | Ciudad | Santo Domingo *(supuesto)* | Santo Domingo | ☐ Confirmar |
| 3.3 | Provincia / estado | Distrito Nacional o provincia real | No documentado | ☐ Confirmar |
| 3.4 | Código postal | *(pendiente)* | `10101` *(ficticio TC-002)* | ☐ Confirmar |
| 3.5 | País | República Dominicana | DO ✅ | ✅ Aceptado |

**Ruta Odoo:** Ajustes → Empresas → [Hellenia] → dirección del contacto vinculado (`res.partner`).

**Criterio de aceptación:** Dirección completa y coherente con registros DGII / contratos Hellenia.

---

### 4. Teléfono

| # | Campo | Valor propuesto | Estado actual DEV | Estado |
|---|-------|-----------------|-------------------|--------|
| 4.1 | Teléfono principal | *(pendiente)* | +1 809-555-0100 *(ficticio)* | ☐ Confirmar |
| 4.2 | Móvil / WhatsApp comercial | *(pendiente)* | — | ☐ Opcional |
| 4.3 | Formato | +1 809-XXX-XXXX o +1 829-XXX-XXXX | Estándar RD | ☐ Confirmar |

---

### 5. Correo

| # | Campo | Valor propuesto | Estado actual DEV | Estado |
|---|-------|-----------------|-------------------|--------|
| 5.1 | Email empresa / fiscal | *(pendiente — ej. `info@hellenia.cloud` o dominio corporativo)* | Vacío | ☐ Confirmar |
| 5.2 | Email contabilidad | *(pendiente)* | — | ☐ Confirmar |
| 5.3 | Servidor saliente DEV | No configurar producción | [UNREGISTERED_ENTERPRISE_LIMITATIONS.md](UNREGISTERED_ENTERPRISE_LIMITATIONS.md) | ✅ Política |

**Nota:** En laboratorio DEV no activar envío masivo a clientes reales.

---

### 6. País

| # | Campo | Valor | Estado actual | Acción |
|---|-------|-------|---------------|--------|
| 6.1 | País compañía | República Dominicana (`DO`) | ✅ Configurado | Verificar no revertir |
| 6.2 | País fiscal | DO | ✅ | Coherente con `l10n_do` |
| 6.3 | Código ISO | `DO` | ✅ | — |

---

### 7. Moneda

| # | Campo | Valor | Estado actual | Acción |
|---|-------|-------|---------------|--------|
| 7.1 | Moneda compañía | **DOP** (RD$) | ✅ Configurado | Mantener |
| 7.2 | Moneda secundaria | USD *(solo si operan importaciones)* | No documentado | ☐ Confirmar necesidad |
| 7.3 | Tipo de cambio | Manual / automático | No configurado | ☐ Fase 9 Contabilidad |
| 7.4 | Redondeo | Estándar Odoo 2 decimales | Por defecto | Verificar en asientos piloto |

---

### 8. Zona horaria

| # | Campo | Valor propuesto | Estado actual | Acción |
|---|-------|-----------------|---------------|--------|
| 8.1 | Zona horaria compañía | `America/Santo_Domingo` | Admin en `America/Santo_Domingo` (TC-002) | ☐ Verificar en `res.company` |
| 8.2 | Formato fecha | DD/MM/YYYY (es_DO) | Idioma `es_DO` activado | ☐ Confirmar en UI |
| 8.3 | Inicio año fiscal | 1 enero *(estándar RD)* | Por defecto Odoo | ☐ Confirmar con contador |

**Impacto:** Cortes diarios, POS, vencimientos, crons.

---

### 9. Bancos

| # | Ítem | Valor propuesto | Estado | Nota consultor |
|---|------|-----------------|--------|----------------|
| 9.1 | Banco principal | *(pendiente — nombre entidad)* | ☐ Confirmar | Ej. BHD, Popular, Banreservas, etc. |
| 9.2 | Número de cuenta RD$ | *(pendiente)* | ☐ Confirmar | No commitear en Git |
| 9.3 | Tipo cuenta | Corriente / ahorro | ☐ Confirmar | |
| 9.4 | Titular | Hellenia, S.R.L. | ☐ Confirmar | Debe coincidir con razón social |
| 9.5 | SWIFT / IBAN | Solo si transferencias internacionales | ☐ Opcional | `base_iban` disponible |
| 9.6 | Sincronización bancaria live | **No** en DEV | ✅ Política | [IMPLEMENTATION_MASTER_PLAN.md](IMPLEMENTATION_MASTER_PLAN.md) |
| 9.7 | Cuenta contable vinculada | Del plan `do` — cuenta bancos | ☐ Validar con contador | Tras identificar cuenta en plan |

**Ruta Odoo:** Contabilidad → Configuración → Bancos → Cuentas bancarias (o ficha empresa → pestaña bancos).

---

### 10. Diarios

**Estado actual (post TC-002 / plan `do`):** 7 diarios precargados.

| Código / nombre | Tipo Odoo | Uso previsto Hellenia | Estado | Acción Fase 3 |
|-----------------|-----------|----------------------|--------|---------------|
| **FACTU** / Customer Invoices | Ventas | Facturación cliente B01/B02 | ✅ Existe | Revisar cuentas por defecto; nombre en español si aplica |
| **INV** / Vendor Bills | Compras | Facturas proveedor | ✅ Existe | Vincular diario compras |
| **BNK1** / Bank | Banco | Movimientos bancarios | ✅ Existe | Vincular a cuenta banco §9 |
| **MISCE** / Miscellaneous | Varios | Asientos manuales | ✅ Existe | Reservar para ajustes |
| **CABA** / Cash Basis | Criterio de caja | Si aplica régimen | ✅ Existe | ☐ Confirmar con contador si se usa |
| **CAMBI** / Exchange Difference | Diferencia cambio | Solo si hay USD | ✅ Existe | Activar si moneda secundaria |
| **TAX** / Tax Adjustments | Impuestos | Ajustes ITBIS | ✅ Existe | Uso contador |

**Pendiente validar (Fase 3 / contador):**

| Diario adicional | Necesidad | Estado |
|------------------|-----------|--------|
| Efectivo / Caja | POS y cobros menores | ☐ Confirmar si falta o se usa BNK1 |
| POS | Punto de venta | ☐ Fase 8 — crear al configurar POS |
| Tarjeta / clearing | Cobros con datáfono | ☐ Confirmar operación Hellenia |

**Criterio de aceptación:** Cada diario operativo con cuenta predeterminada correcta del plan `do`.

---

### 11. Métodos de pago

Configuración estándar Odoo 19 EE — **sin proveedores de pago externos** en DEV.

| # | Método | Uso Hellenia | Diario sugerido | Estado |
|---|--------|--------------|-----------------|--------|
| 11.1 | **Efectivo** | POS, cobros menores | Caja / efectivo | ☐ Configurar |
| 11.2 | **Transferencia bancaria** | B2B, pagos proveedores | BNK1 | ☐ Configurar |
| 11.3 | **Cheque** | Si aplica operación | BNK1 | ☐ Confirmar uso |
| 11.4 | **Tarjeta débito/crédito** | Retail tienda | Banco + comisiones | ☐ Confirmar |
| 11.5 | **Manual** (payment register) | Laboratorio DEV | — | ✅ Por defecto |

**Ruta Odoo:** Contabilidad → Configuración → Métodos de pago (o Pagos → Configuración).

**Nota:** No activar Stripe, PayPal ni pasarelas reales en DEV.

---

### 12. Categorías de productos

Rubro documentado: **mobiliario y decoración** — retail/distribución.

**Jerarquía propuesta (maestro inicial — sujeta a aprobación Hellenia):**

| Nivel 1 | Nivel 2 (ejemplo) | Tipo | Cuenta ingreso/costo |
|---------|-------------------|------|---------------------|
| **Mobiliario** | Sala, comedor, dormitorio, oficina | Bienes almacenables | Del plan `do` — validar con contador |
| **Decoración** | Iluminación, textiles, accesorios | Bienes almacenables | Idem |
| **Servicios** | Entrega, instalación, diseño | Servicio | Si aplica |
| **Gastos / consumibles** | Embalaje, ferretería menor | Consumible | Compras internas |

| # | Tarea | Estado |
|---|-------|--------|
| 12.1 | Definir árbol de categorías con Hellenia | ☐ Pendiente |
| 12.2 | Asignar cuenta de ingreso por categoría | ☐ Fase 3 + contador |
| 12.3 | Asignar cuenta de costo / valoración | ☐ Fase 7 Inventario |
| 12.4 | Política impuestos por categoría (ITBIS 18% default) | ☐ Validar excepciones |
| 12.5 | Crear 3–5 categorías piloto en DEV | ☐ Post-aprobación |

**Ruta Odoo:** Inventario → Configuración → Categorías de producto.

---

### 13. Proveedores iniciales

Maestro mínimo para pruebas de compras (Fase 6) — **datos ficticios o reales según apruebe Hellenia**.

| # | Proveedor tipo | RNC ejemplo | Propósito | Estado |
|---|----------------|-------------|-----------|--------|
| 13.1 | Proveedor formal (mobiliario) | *(pendiente RNC real)* | PO + factura B01 entrada | ☐ Pendiente |
| 13.2 | Proveedor servicios (transporte/instalación) | *(pendiente)* | Retenciones ISR/ITBIS | ☐ Pendiente |
| 13.3 | Proveedor informal (pruebas B11) | Sin RNC o cédula | TC-029 futuro | ☐ Laboratorio |
| 13.4 | Términos de pago | 30 / 60 días | Estándar compras | ☐ Confirmar |
| 13.5 | Moneda proveedor | DOP (default) | — | ☐ Confirmar importadores USD |

**Campos obligatorios partner proveedor RD:**

- Nombre legal
- RNC (`vat`) si proveedor formal
- País DO
- Cuenta payable del plan `do`
- Posición fiscal si aplica retención

**Cantidad sugerida Fase 3:** 2–3 proveedores piloto (no catálogo completo).

---

### 14. Responsables contables

Referencias internas Hellenia para decisiones de parametrización — **no crean usuarios Odoo en esta fase**.

| Rol | Nombre / contacto | Responsabilidad | Estado |
|-----|-------------------|-----------------|--------|
| Contador / CPA Hellenia | *(pendiente)* | Validar plan cuentas, diarios, impuestos | ☐ Confirmar |
| Representante fiscal DGII | *(pendiente)* | Rangos NCF, calendario declaraciones | ☐ Confirmar |
| Contacto operativo Hellenia | *(pendiente)* | Maestros productos, proveedores, POS | ☐ Confirmar |
| Consultor Justech | Equipo implementación | Parametrización DEV, documentación | ✅ Activo |
| Aprobador cambios DEV | *(pendiente)* | Gate antes de apply en VPS | ☐ Confirmar |

**Nota:** Los responsables se documentan en acta interna; no se almacenan datos personales sensibles en Git sin acuerdo.

---

### 15. Datos pendientes por confirmar

Lista consolidada para reunión de kick-off / aprobación con Hellenia:

| ID | Tema | Pregunta para Hellenia | Impacto si no se confirma |
|----|------|------------------------|---------------------------|
| P-01 | RNC oficial | ¿`133621282` es el RNC correcto y vigente? | Bloquea identidad fiscal en documentos |
| P-02 | Razón social exacta | ¿Texto legal completo para facturas? | Encabezado documentos |
| P-03 | Dirección fiscal DGII | Calle, ciudad, provincia, CP oficiales | Facturas, reportes |
| P-04 | Teléfono y email corporativo | Datos de contacto en documentos | PDF, pie de factura |
| P-05 | Logo | Archivo PNG/SVG alta resolución | Branding |
| P-06 | Banco(s) y cuentas | Entidad, número, tipo (solo uso interno) | Diario BNK1, pagos |
| P-07 | ¿Operan en USD? | Importaciones / proveedores extranjeros | Moneda secundaria, CAMBI |
| P-08 | ¿Usan efectivo/POS? | Necesidad diario caja y método efectivo | Fase 8 POS |
| P-09 | ¿Emiten cheques? | Activar `l10n_do_check_printing` más adelante | Compras |
| P-10 | Árbol categorías producto | Estructura real del catálogo | Inventario, márgenes |
| P-11 | Proveedores piloto | 2–3 proveedores reales o autorización ficticios | Compras Fase 6 |
| P-12 | Contador referente | Nombre y canal de validación plan cuentas | Cuentas por categoría |
| P-13 | Empresa TC-002 vs legal | ¿Renombrar `Hellenia Pruebas RD` → `Hellenia, S.R.L.` o empresa nueva? | Estrategia BD DEV |
| P-14 | Actividad económica DGII | Código / descripción si campo existe en UI | Reportes futuros |
| P-15 | Propina 10% | ¿Aplica rubro restaurante/hospitalidad? | Impuesto propina `l10n_do` |
| P-16 | Multi-almacén / tiendas | ¿Una o varias ubicaciones físicas? | Fase 7 Inventario, Fase 8 POS |
| P-17 | Backup antes de apply | Confirmar ventana para `backup-dev.sh` | Rollback |

---

## Secuencia de ejecución propuesta (tras aprobación)

Orden recomendado para minimizar retrabajo:

```
1. backup-dev.sh + verificación
2. Actualizar datos legales empresa (§1–§8)
3. Revisar / completar bancos (§9)
4. Revisar diarios y cuentas por defecto (§10)
5. Configurar métodos de pago (§11)
6. Crear categorías producto piloto (§12)
7. Crear proveedores piloto (§13)
8. Documentar responsables (§14) — acta, no Git si sensible
9. Captura evidencia + checklist marcado
10. NO crear usuarios; NO TC-003
```

**Ruta UI principal:** Ajustes → Empresas → Hellenia, S.R.L.

**Alternativa técnica:** Script controlado vía `odoo shell` (mismo patrón TC-002) — solo si Hellenia aprueba.

---

## Criterios de salida Fase 3 (empresa)

| # | Criterio | Verificación |
|---|----------|--------------|
| E1 | Razón social y RNC oficial cargados | UI + export partner empresa |
| E2 | País DO, moneda DOP, timezone Santo Domingo | `res.company` |
| E3 | Dirección, teléfono, email completos (datos aprobados) | Ficha contacto |
| E4 | Al menos 1 cuenta bancaria empresa (si aplica operación) | Sin sync live |
| E5 | Diarios revisados con cuentas del plan `do` | Contabilidad → Diarios |
| E6 | Métodos de pago base configurados | Pagos |
| E7 | ≥3 categorías producto piloto | Inventario |
| E8 | ≥2 proveedores piloto | Contactos |
| E9 | Backup post-configuración | `backups/dev/` |
| E10 | Sin usuarios nuevos; TEST/PROD intactos | `res.users` count = 1 |

---

## Aprobación requerida

| Campo | Valor |
|-------|-------|
| Documento | `docs/PHASE-3-COMPANY-CONFIG-CHECKLIST.md` |
| Acción siguiente | **Esperar aprobación cliente** para aplicar en DEV |
| Confirmación mínima | Resolver **P-01 a P-04** y **P-13** antes de ejecutar |

**Mensaje de aprobación sugerido:**

> Aprobado checklist Fase 3. Confirmo RNC [valor], dirección [valor], renombrar empresa a Hellenia S.R.L. Proceder backup y parametrización en DEV.

---

## Referencias

- [PROJECT_STRATEGY.md](PROJECT_STRATEGY.md) — Estrategia v3.0
- [IMPLEMENTATION_MASTER_PLAN.md](IMPLEMENTATION_MASTER_PLAN.md) — Fase 3 detalle histórico
- [TC-002-RESULT.md](TC-002-RESULT.md) — Estado actual empresa prueba
- [GAP_ANALYSIS_RD.md](GAP_ANALYSIS_RD.md) — Limitaciones conocidas (no bloquean Fase 3)

---

**Mantenido por:** Justech — Consultoría Odoo Enterprise  
**Próximo paso:** Aprobación del cliente con datos §15 resueltos → entonces aplicar parametrización en DEV.
