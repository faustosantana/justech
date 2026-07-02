# TC-002 — Empresa dominicana de pruebas y validación fiscal post-configuración

**Fecha ejecución:** 2026-06-30 (UTC)  
**Entorno:** `hellenia_dev` — https://dev.hellenia.cloud  
**Build Odoo:** `19.0+e-20260619`  
**Prerequisito:** TC-001 PASS

---

## Resumen ejecutivo

| Ítem | Resultado |
|------|-----------|
| Instalación de módulos | ✅ **No ejecutada** (ya instalados por TC-001 / `auto_install`) |
| Empresa dominicana de pruebas | ✅ **PASS** |
| Plan contable `do` cargado | ✅ **PASS** — 288 cuentas |
| Impuestos ITBIS | ✅ **PASS** — 14 impuestos ITBIS |
| Posiciones fiscales | ✅ **PASS** — 11 posiciones |
| Diarios contables | ✅ **PASS** — 7 diarios |
| Tipos documento fiscal | ❌ **0 registros** |
| Secuencias NCF (B01–B13) | ❌ **0 registros** |
| Modelos LATAM (`l10n_latam*`) | ❌ **Ausentes** |
| Infraestructura DEV | ✅ **PASS** |
| Usuarios creados | ✅ **0** (solo `admin` existente) |

**Conclusión TC-002:** **PASS parcial** — empresa RD configurada y datos contables base cargados. **G-01 confirmada** y **G-02 reforzada**: sin tipos documento fiscal ni secuencias NCF tras configuración completa de empresa dominicana.

---

## 1. Alcance ejecutado

Según aprobación del cliente:

- **No** instalar módulos adicionales
- **No** desinstalar `l10n_do_reports` ni `l10n_do_check_printing` (stack oficial aceptado)
- **No** crear usuarios
- **No** ejecutar wizard de onboarding
- **No** tocar TEST ni PRODUCCIÓN

**Acción:** Configurar empresa de pruebas dominicana y re-validar datos fiscales.

---

## 2. Empresa de pruebas configurada

| Campo | Valor |
|-------|-------|
| Nombre | Hellenia Pruebas RD |
| País | República Dominicana (`DO`) |
| Moneda | DOP (activada e asignada) |
| RNC (ficticio) | `131793916` |
| Dirección | Av. Winston Churchill 123, Santo Domingo 10101 |
| Teléfono | +1 809-555-0100 |
| Plan contable | `do` (Dominican Republic) |
| Zona horaria (admin) | `America/Santo_Domingo` |
| Idioma (admin) | `es_DO` (activado) |

**Método:** `odoo shell` — actualización `res.company` / `res.partner` + `account.chart.template.try_loading('do', company)`.

---

## 3. Validación post-configuración

### 3.1 Disponible tras empresa DO

| Verificación | Cantidad | Evidencia |
|--------------|----------|-----------|
| Cuentas contables | **288** | Plan `do` cargado |
| Impuestos ITBIS | **14** | 18%, 16%, 9%, 8%, exento, retenciones parciales ITBIS |
| Impuestos totales | **37** | Incluye ISR (-2% a -27%), propina, etc. |
| Posiciones fiscales | **11** | DO Domestic, Governmental, Restaurants, etc. |
| Diarios | **7** | INV, FACTU, BNK1, MISCE, CABA, CAMBI, TAX |

**Muestra impuestos ITBIS:**

- 18% ITBIS (venta/compra)
- 16% ITBIS
- 9% / 8% ITBIS (L690-16)
- ITBIS Exempt
- Retenciones ITBIS (-30%, -75%, -100% variantes)

**Muestra posiciones fiscales:**

- DO Domestic
- Governmental
- Informal Supplier of Goods
- Restaurants / To Take Away
- P. Physical Services / P. Legal Services

### 3.2 No disponible tras empresa DO

| Verificación | Resultado | Impacto |
|--------------|-----------|---------|
| `l10n_latam.document.type` | Modelo **ausente** — 0 registros | Sin tipos B01/B02/B03/B04 |
| Secuencias NCF | **0** (B01–B13 todos en 0) | Sin numeración fiscal |
| Modelos `l10n_latam*` | **0** en `ir.model` | Framework LATAM no presente en build 19.0 |

---

## 4. Infraestructura

| Check | Resultado |
|-------|-----------|
| HTTP `/web/login` | 200 |
| Odoo container | healthy |
| PostgreSQL container | healthy |
| Tracebacks post-configuración | ninguno |
| Usuarios en BD | **1** (`admin`) |

---

## 5. Decisión G-01

Criterio acordado con el cliente:

> Si después de crear la empresa siguen sin aparecer los documentos fiscales, entonces sí confirmar G-01.

| Condición | Cumplida |
|-----------|----------|
| Empresa dominicana configurada | ✅ |
| Plan contable `do` cargado | ✅ |
| Tipos documento fiscal presentes | ❌ |
| Secuencias NCF presentes | ❌ |

**G-01 → Limitación conocida de plataforma** — TC-002 documentó ausencia de tipos documento y secuencias NCF en el build on-premise actual. Registrada en [GAP_ANALYSIS_RD.md](GAP_ANALYSIS_RD.md). **No bloquea** la implementación (v3.0 [PROJECT_STRATEGY.md](PROJECT_STRATEGY.md)).

**G-02 → Reforzada** — ausencia total de modelos `l10n_latam*` tras TC-002.

---

## 6. Evidencia

| Archivo | Ubicación |
|---------|-----------|
| Log configuración + validación | `evidence/l10n-do-tests/2026-06-30/TC-002/configure-company.log` |
| Resultado JSON | `evidence/l10n-do-tests/2026-06-30/TC-002/result.json` |
| TC-001 (prerequisito) | `docs/TC-001-RESULT.md` |

---

## 7. Conclusión

TC-002 cumplió el objetivo de configurar la empresa dominicana de pruebas y re-validar el stack fiscal. Los datos contables base de `l10n_do` **sí** se cargan correctamente al aplicar el plan `do`. Los componentes críticos para NCF tradicional — **tipos de documento fiscal y secuencias NCF** — **no aparecen** en Odoo 19.0 EE on-premise tras configuración completa.

**Implicación:** Desarrollo custom en `hellenia_account` (o evaluación upgrade 19.3+) requerido para NCF operativo. TC-020 (asignación NCF en factura) sigue siendo prueba crítica de desempate operativo.

**Estado:** TC-002 completado. Continuar implementación funcional — [PROJECT_STRATEGY.md](PROJECT_STRATEGY.md).
