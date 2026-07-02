# Implementación NCF Tradicional — Hellenia

**Cliente:** Hellenia, S.R.L. — República Dominicana  
**Ambiente:** `hellenia_dev` (laboratorio)  
**Build:** Odoo `19.0+e-20260619` on-premise  
**Fecha:** 2026-06-30  
**Estado:** Documentación de preparación — **sin configuración ejecutada**

---

## Declaración de alcance

### Etapa 1 — En alcance

| Capacidad | Módulo / mecanismo |
|-----------|-------------------|
| NCF tradicional (papel / impreso) | `l10n_do` |
| Plan contable DGII/NIIF | `l10n_do` |
| ITBIS, retenciones, propina | `l10n_do` |
| Facturación fiscal con comprobante | `l10n_do` + diarios con documentos |
| Libros y reportes fiscales RD | `l10n_do_reports` |
| Suite contable Enterprise | `account_accountant`, `account_reports` |

### Fuera de alcance Etapa 1

| Capacidad | Motivo |
|-----------|--------|
| eNCF / ECF electrónico | Decisión de proyecto — Fase futura independiente |
| `l10n_do_edi` | Solo eNCF; **no instalar** |
| Infile | Solo integración eNCF |
| Comunicación electrónica DGII | Requiere `l10n_do_edi` + Infile |

---

## Confirmación oficial: ¿`l10n_do` + `l10n_do_reports` son suficientes?

### Evidencia documental Odoo

Fuente: [Dominican Republic — Odoo saas-19.3](https://www.odoo.com/documentation/saas-19.3/applications/finance/fiscal_localizations/dominican_republic.html)

| Módulo | Descripción oficial | ¿Requerido para NCF tradicional? |
|--------|---------------------|-------------------------------|
| **`l10n_do`** | *"The default fiscal localization package... the **minimum configuration required** for a company to operate in the Dominican Republic according to the **DGII guidelines**."* | ✅ **Sí** — base obligatoria |
| **`l10n_do_reports`** | *"Provides **financial reports tailored** to the Dominican Republic's regulatory requirements."* | ✅ **Sí** — libros/reportes fiscales |
| **`l10n_do_edi`** | *"Generate and validate **Electronic Fiscal Receipts (ECF)** with XML, **eNCF**, digital signatures... DGII."* | ❌ **No** — exclusivo eNCF |
| **`l10n_do_check_printing`** | Formato cheques bancarios RD | ⚠️ Opcional — solo si pagan con cheques |

Cita oficial sobre instalación:

> *"The localization's **core modules** are installed automatically with the localization. **The rest can be manually installed.**"*

Interpretación para Hellenia:

- **`l10n_do`** = módulo core → se auto-instala al configurar país DO.
- **`l10n_do_edi`** = módulo adicional → **no forma parte del core**; documentado únicamente para facturación electrónica con Infile.
- **`l10n_do_reports`** = módulo adicional Enterprise → instalar manualmente (o vía `auto_install` tras `account_reports`).

### Evidencia en código `l10n_do` (Odoo 19.0 — build Hellenia)

Manifest oficial (`addons/l10n_do/__manifest__.py`, rama `19.0`):

| Elemento | Contenido |
|----------|-----------|
| `depends` | `account`, `base_iban` |
| `auto_install` | `['account']` |
| Secuencias NCF declaradas | Facturas valor fiscal, consumidor final, ND/NC, proveedores informales, ingreso único, gastos menores, gubernamentales |
| Impuestos declarados | ITBIS compras/ventas, retenciones ITBIS/ISR, grupos por sector |
| Tax report | `data/account_tax_report_data.xml` — estructura declaración ITBIS (casillas II, III, retenciones) |

**Advertencia del manifest (texto legacy en 19.0):**

> *"Esta localización, aunque posee las secuencias para NCF, las mismas no pueden ser utilizadas sin la instalación de módulos de terceros o desarrollo adicional."*

**Acción requerida en Fase 2–3:** Validar en UI de DEV que las secuencias NCF operan con el stack oficial `l10n_do` + `l10n_do_reports` **sin** módulos de terceros. Si la advertencia persiste operativamente, documentar brecha y evaluar custom (`hellenia_account`) — no asumir resuelto hasta prueba.

### Evolución en saas-19.3 (referencia, no build actual)

En `saas-19.3`, `l10n_do` añade dependencia de `l10n_latam_invoice_document` y tipos de documento E31–E34 en datos XML. Eso confirma que el framework LATAM de documentos fiscales es el mecanismo Odoo para NCF/eNCF, pero los tipos **electrónicos** están en `l10n_do_edi` y datos E31–E34. Hellenia en **19.0** no tiene esa evolución completa; operará con el modelo de secuencias del manifest 19.0.

### Conclusión consultoría

| Pregunta | Respuesta |
|----------|-----------|
| ¿`l10n_do` + `l10n_do_reports` bastan para Etapa 1? | **Sí**, según documentación oficial: base DGII en `l10n_do`; reportes regulatorios en `l10n_do_reports`; eNCF es módulo separado opcional. |
| ¿Hace falta `l10n_do_edi`? | **No** — explícitamente fuera de alcance. |
| ¿Otros módulos oficiales necesarios? | Ver § Módulos oficiales requeridos. |
| ¿Riesgo en 19.0 on-premise? | Manifest legacy + documentación RD detallada solo en saas-19.3 → **validación obligatoria** en DEV antes de go-live. |

---

## Módulos oficiales requeridos

### Stack mínimo Etapa 1 (NCF tradicional)

```
account                    (core contabilidad)
    └── l10n_do            (auto_install — localización RD)
            └── account_reports      (Enterprise — reportes contables)
                    └── l10n_do_reports  (auto_install — reportes fiscales RD)
```

### Suite contable Enterprise (recomendada)

| Módulo | Rol | Justificación |
|--------|-----|---------------|
| `account_accountant` | Contabilidad avanzada EE | Cierre, conciliación, informes |
| `account_reports` | Motor reportes EE | Prerrequisito `l10n_do_reports` |

### Módulos de aplicación (no fiscal, requeridos por flujo operativo)

| Módulo | Fase | Rol |
|--------|------|-----|
| `stock` | Inventario | Movimientos, valorización |
| `purchase` | Compras | PO, facturas proveedor |
| `sale` | Ventas | Cotizaciones, facturas cliente |
| `point_of_sale` | POS | Venta tienda |

### Módulos explícitamente excluidos

| Módulo | Motivo exclusión |
|--------|------------------|
| `l10n_do_edi` | eNCF / Infile / DGII electrónico |
| Cualquier módulo OCA/tercero NCF | Política proyecto: solo stack oficial |

### Módulos opcionales

| Módulo | Cuándo |
|--------|--------|
| `l10n_do_check_printing` | Hellenia emite cheques bancarios formato RD |
| `stock_barcode` | Alto volumen almacén |
| `approvals` | Control aprobación compras/gastos |

---

## Tipos de NCF soportados

### Mapeo manifest `l10n_do` → tipos DGII

El manifest de `l10n_do` declara secuencias preconfiguradas. Correspondencia con nomenclatura DGII (Norma General 06-2018 y actualizaciones):

| Código DGII | Nombre fiscal | Uso Hellenia | Secuencia manifest `l10n_do` |
|-------------|---------------|--------------|------------------------------|
| **B01** | Factura de Crédito Fiscal | Ventas B2B — cliente con RNC, genera crédito ITBIS | Facturas con Valor Fiscal |
| **B02** | Factura de Consumo | Ventas B2C — consumidor final, POS | Facturas para Consumidores Finales |
| **B03** | Nota de Débito | Ajustes que incrementan monto factura original | Notas de Débito |
| **B04** | Nota de Crédito | Devoluciones, descuentos post-factura | Notas de Crédito |
| **B11** | Comprobante Proveedores Informales | Compras a proveedores sin RNC formal | Registro Proveedores Informales |
| **B12** | Registro Único de Ingresos | Ingresos no operacionales puntuales | Registro de Ingreso Único |
| **B13** | Gastos Menores | Gastos menores sin factura formal | Registro de Gastos Menores |
| **B14** | Regímenes Especiales | Ventas a zonas francas / regímenes especiales | (validar en UI) |
| **B15** | Gubernamental | Ventas a entidades gubernamentales | Gubernamentales |
| **B16** | Exportaciones | Ventas al exterior | (validar en UI — export en tax report) |

### Tipos prioritarios Hellenia (definir en kick-off negocio)

| Prioridad | Tipo | Canal típico |
|-----------|------|--------------|
| 🔴 P0 | B02 | POS, retail consumidor final |
| 🔴 P0 | B01 | Ventas B2B con RNC |
| 🟠 P1 | B04 / B03 | Devoluciones y ajustes |
| 🟠 P1 | B11 | Compras informales |
| 🟡 P2 | B14, B15, B16 | Según operación real Hellenia |

### Equivalencia eNCF (solo referencia — Fase futura)

| NCF tradicional | eNCF (NO implementar ahora) |
|---------------|----------------------------|
| B01 | E31 |
| B02 | E32 |
| B03 | E33 |
| B04 | E34 |

---

## Configuración requerida

### 1. Empresa (`res.company`)

| Campo | Valor | Obligatorio | Fuente |
|-------|-------|-------------|--------|
| País | República Dominicana | ✅ | Doc saas-19.3 |
| Moneda | DOP (RD$) | ✅ | Doc saas-19.3 |
| RNC | Número DGII Hellenia | ✅ | Doc saas-19.3 — *"required for all electronic fiscal documents"* (aplica también a identidad fiscal empresa) |
| Dirección fiscal | Calle, ciudad, provincia, CP, país | ✅ | Doc saas-19.3 |
| Zona horaria | `America/Santo_Domingo` | ✅ | Operación local |

### 2. Contactos / Partners

| Tipo partner | Campo | Uso NCF |
|--------------|-------|---------|
| Cliente B2B | RNC (`vat`) | Determina tipo B01 vs B02 |
| Cliente B2C | Sin RNC o cédula según monto | B02 consumo |
| Proveedor | RNC | Facturas compra, retenciones |
| Tipo identificación LATAM | RNC, cédula, pasaporte | `l10n_latam_identification_type` (saas-19.3; validar en 19.0) |

### 3. Instalación módulos (orden propuesto)

```
1. account_accountant     (si no instalado)
2. l10n_do                  (auto al país DO, o manual)
3. account_reports          (si no auto con accountant)
4. l10n_do_reports          (auto tras l10n_do + account_reports)
```

**No instalar:** `l10n_do_edi`

### 4. Plan contable

- Cargar plantilla `do` vía configuración fiscal (paquete DO).
- Revisar cuentas con contador Hellenia antes de asientos reales.
- Cuentas clave preconfiguradas en `template_do.py`: CxC, CxP, ITBIS venta/compra, diferencial cambio.

### 5. Impuestos

Preconfigurados en `l10n_do` (validar activos tras instalación):

| Impuesto | Tasa | Uso |
|----------|------|-----|
| ITBIS ventas | 18% | Tasa estándar |
| ITBIS ventas | 16% | Bienes tasa reducida |
| ITBIS ventas | 0% | Tasa cero |
| ITBIS exento | — | Exenciones |
| ITBIS compras | 18% / 16% | Crédito fiscal |
| Retención ITBIS | Variable | Servicios según DGII |
| Retención ISR | Variable | Honorarios, alquileres, etc. |
| Propina | 10% | Solo si rubro hospitalidad aplica |

Tax report ITBIS: estructura en `account_tax_report_data.xml` (casillas II-1, II.A, II.B, III liquidación, retenciones).

### 6. Posiciones fiscales

Preconfiguradas en `l10n_do` para automatizar:

- Exenciones (ventas al Estado)
- Retenciones (compras servicios exterior)
- Cambios de impuesto según tipo operación

---

## Secuencias y rangos NCF

### Proceso DGII (externo a Odoo)

1. Solicitar autorización de comprobantes fiscales en portal DGII.
2. Recibir rangos por tipo (ej. B02-00000001 a B02-00050000).
3. Registrar fecha de vencimiento del rango.
4. Configurar en Odoo antes de emitir.

### Configuración en Odoo

| Elemento | Configuración | Notas |
|----------|---------------|-------|
| **Tipos de documento** | Contabilidad → Configuración → Tipos de documento | Validar nombres/códigos tras instalar `l10n_do` |
| **Rangos autorizados** | Por tipo de documento — secuencia inicio, fin, vencimiento | Equivalente a "Document Range" en doc saas-19.3 pero para NCF tradicional |
| **Secuencia** | Vinculada a tipo de documento + diario | Framework LATAM en versiones recientes; secuencias journal en 19.0 |
| **Consumo** | Al confirmar factura | Sistema asigna próximo NCF del rango activo |

### Formato NCF tradicional

```
B02 0000000123
│││  └──────── secuencial (11 dígitos)
││└─ tipo documento (3 caracteres: B02, B01, etc.)
```

### Reglas operativas

| Regla | Descripción |
|-------|-------------|
| Un rango por tipo | No mezclar B01 y B02 en mismo rango |
| Vencimiento | Renovar ante DGII antes de agotar o expirar |
| Anulación | Registrar en libro 608 (reporte fiscal) |
| NC/ND | Referenciar NCF origen |

---

## Diarios

### Diarios de ventas (NCF salida)

| Diario | Tipo | Use Documents | Tipos NCF |
|--------|------|---------------|-----------|
| Ventas fiscal | Ventas | ✅ Habilitado | B01, B02 según cliente |
| Notas crédito | Ventas | ✅ | B04 |
| Notas débito | Ventas | ✅ | B03 |

Configuración clave (adaptado de doc oficial — sección journals):

- **Tipo:** Sales
- **Use Documents?:** Enabled — obligatorio para selección tipo comprobante fiscal

### Diarios de compras (NCF entrada)

| Diario | Tipo | Use Documents | Tipos NCF |
|--------|------|---------------|-----------|
| Compras | Compras | ✅ (si aplica) | Facturas proveedor |
| Gastos menores | Compras | ✅ | B13 |
| Proveedores informales | Compras | ✅ | B11 |

> En versiones recientes Odoo consolidó diarios de compra usando tipos de documento en un solo diario (PR #62330). Validar estructura en DEV tras `l10n_do`.

### Diarios financieros (sin NCF)

| Diario | Tipo |
|--------|------|
| Banco | Bank |
| Efectivo / Caja | Cash |
| Operaciones varias | Miscellaneous |

### Diario POS

| Diario | Vinculación |
|--------|-------------|
| POS ventas | Tienda POS → diario ventas B02 por defecto |
| Cuenta transitoria | Cierre sesión → banco/efectivo |

---

## Configuración fiscal por flujo

### Ventas B2B (B01)

```
Cliente con RNC → Cotización/Pedido → Entrega → Factura
    → Tipo documento: B01
    → ITBIS 18% en líneas
    → NCF asignado al confirmar
    → Asiento: Ingreso + ITBIS cobrado + CxC
```

### Ventas B2C / POS (B02)

```
Cliente consumidor final → Venta/POS → Pago
    → Tipo documento: B02
    → ITBIS según política precios (incluido/excluido)
    → Ticket/factura con NCF B02
```

### Compras con retención

```
Factura proveedor → Tipo compra → ITBIS crédito fiscal
    → Retención ISR/ITBIS si aplica
    → Asiento: Gasto/Inventario + ITBIS pagado − Retención + CxP
```

### Notas de crédito (B04)

```
Desde factura original → Nota de crédito
    → Referencia NCF origen
    → Tipo B04
    → Reversión parcial/total ingreso e ITBIS
```

---

## Limitaciones actuales

### Limitaciones de alcance (decisión proyecto)

| Limitación | Impacto |
|------------|---------|
| Sin eNCF | No emisión electrónica legal DGII vía Odoo |
| Sin Infile | Sin firma/transmisión XML |
| Sin `l10n_do_edi` | Sin flujo E31–E34 |

### Limitaciones técnicas build 19.0 Hellenia

| Limitación | Detalle | Mitigación |
|------------|---------|------------|
| `l10n_do_edi` ausente en tarball | No aplica — fuera de alcance | — |
| Documentación RD 19.0 incompleta | URL país → 404 en doc 19.0 | Usar saas-19.3 como referencia funcional + validar en DEV |
| Manifest legacy NCF | Texto advierte terceros para secuencias | **Prueba obligatoria** Fase 2–3 |
| `l10n_do` 19.0 sin `l10n_latam_invoice_document` en depends | Modelo documentos puede diferir de saas-19.3 | Documentar hallazgos en acta Fase 2 |
| Detalle reportes `l10n_do_reports` | Doc no lista 606/607/608/IT-1 explícitamente | Validar menú tras instalar; foro Odoo sin respuesta oficial aún |
| Licencia Enterprise sin registrar | Trial puede expirar | Monitorear `database.expiration_date` |
| Declaraciones DGII | Formatos 606/607/608 pueden requerir exportación manual según reportes disponibles | Confirmar con contador en UAT |

### Limitaciones legales / regulatorias

| Tema | Nota |
|------|------|
| Ley 32-23 facturación electrónica | Migración obligatoria a e-CF en plazos DGII — planificar Fase Futura eNCF |
| NCF papel | Válido mientras DGII mantenga autorización y rangos tradicionales vigentes |
| Formatos impresos | Responsabilidad empresa cumplir requisitos mínimos DGII en documento impreso/PDF |

---

## Preparación futura para eNCF (Fase independiente)

> **No ejecutar en Etapa 1.** Este apartado existe solo para no bloquear decisiones actuales y facilitar migración posterior.

### Cuándo activar Fase Futura eNCF

- DGII exija e-CF para el perfil de Hellenia
- Decisión dirección migrar a facturación electrónica
- Disponibilidad `l10n_do_edi` en build on-premise estable (19.3+ o tarball actualizado)

### Prerrequisitos futuros

| Requisito | Responsable |
|-----------|-------------|
| Upgrade Odoo con `l10n_do_edi` en imagen | Justech (infra — fuera Etapa 1) |
| Contrato Infile | Hellenia |
| Registro emisor electrónico DGII | Hellenia |
| Rangos eNCF (E31–E34) | DGII |
| Credenciales Infile Test → Prod | Infile + configuración Odoo |
| Licencia Enterprise registrada | Go-live PROD |

### Decisiones Etapa 1 que facilitan eNCF futuro

| Decisión ahora | Beneficio futuro |
|----------------|------------------|
| RNC correcto en empresa y partners | Validación ECF |
| Diarios ventas con **Use Documents** | Misma estructura para E31/E32 |
| Tipos documento y rangos bien configurados | Migración rangos eNCF |
| `income_type` / clasificación ingresos | Campo requerido en ECF (doc saas-19.3) |
| Sin custom que parchee `l10n_do*` | Upgrade limpio a `l10n_do_edi` |
| Maestros limpios (productos, impuestos, partners) | Reutilización directa |

### Módulos Fase Futura

```
l10n_do_edi          (Enterprise — eNCF)
+ Infile             (servicio externo)
+ Config DGII        (rangos E31–E34)
```

Documentación de referencia: [INFILE-REQUIREMENTS.md](INFILE-REQUIREMENTS.md) (archivo congelado hasta activar fase).

---

## Checklist de validación (pre-go-live NCF tradicional)

| # | Validación | Fase |
|---|------------|------|
| 1 | `l10n_do` instalado, país = DO | 2 |
| 2 | `l10n_do_reports` instalado | 2 |
| 3 | `l10n_do_edi` **no** instalado | 2 |
| 4 | Plan contable RD cargado | 3 |
| 5 | ITBIS 18% correcto en factura prueba | 3 |
| 6 | Retención aplicada en compra prueba | 3 |
| 7 | Rango NCF B02 configurado | 3 |
| 8 | Factura B02 con NCF asignado | 3 |
| 9 | Factura B01 con RNC cliente | 5 |
| 10 | NC B04 referencia NCF origen | 5 |
| 11 | POS emite B02 | 7 |
| 12 | Reportes fiscales `l10n_do_reports` visibles | 8 |
| 13 | Tax report ITBIS cuadra | 8 |

---

## Referencias

| Fuente | URL |
|--------|-----|
| Fiscal localizations Odoo 19.0 | https://www.odoo.com/documentation/19.0/applications/finance/fiscal_localizations.html |
| Dominican Republic saas-19.3 | https://www.odoo.com/documentation/saas-19.3/applications/finance/fiscal_localizations/dominican_republic.html |
| Manifest `l10n_do` 19.0 | https://github.com/odoo/odoo/blob/19.0/addons/l10n_do/__manifest__.py |
| Foro documentos soportados | https://www.odoo.com/forum/help-1/l10n-do-documentos-soportados-nueva-localizacion-republica-dominicana-302531 |
| Plan maestro implementación | [IMPLEMENTATION_MASTER_PLAN.md](IMPLEMENTATION_MASTER_PLAN.md) |

---

**Versión:** 1.0  
**Mantenido por:** Consultoría implementación Justech  
**Próximo paso:** Aprobación Fase 1 — sin ejecutar configuración hasta confirmación explícita
