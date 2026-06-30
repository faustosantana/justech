# Plan Maestro de Implementación — Hellenia Odoo Enterprise 19

**Rol:** Consultor Senior de Implementación Odoo Enterprise  
**Cliente:** Hellenia, S.R.L. — República Dominicana  
**Ambiente de trabajo:** `hellenia_dev` (DEV laboratorio)  
**Fecha:** 2026-06-30  
**Versión:** 2.0  
**Estado:** Fase funcional iniciada — **sin ejecución de configuración aún**

---

## Alcance Etapa 1 — NCF tradicional

| En alcance | Fuera de alcance (Fase Futura eNCF) |
|------------|-------------------------------------|
| NCF tradicional (papel/impreso) | eNCF / ECF electrónico |
| Facturación fiscal RD | `l10n_do_edi` |
| Contabilidad dominicana (DGII/NIIF) | Infile |
| ITBIS, retenciones, propina | Comunicación electrónica DGII |
| Libros y reportes `l10n_do_reports` | |

**Stack fiscal Etapa 1:** `l10n_do` + `l10n_do_reports` (+ suite contable Enterprise).  
**Documento técnico NCF:** [NCF_IMPLEMENTATION.md](NCF_IMPLEMENTATION.md)

### Flujo de implementación Etapa 1

```
Empresa → Contabilidad RD + NCF tradicional → Inventario → Compras → Ventas → POS → Reportes
```

---

## Declaración de cambio de fase

| Fase anterior | Estado |
|---------------|--------|
| Infraestructura (Docker, Enterprise, backups, Git) | ✅ **Congelada** — ver [§ Infraestructura congelada](#infraestructura-congelada) |
| Licencia `M260616306091776` | ⏸️ Diferida hasta go-live — ver [UNREGISTERED_ENTERPRISE_LIMITATIONS.md](UNREGISTERED_ENTERPRISE_LIMITATIONS.md) |

| Fase actual | Objetivo |
|-------------|----------|
| **Implementación funcional** | Dejar Hellenia completamente parametrizada para iniciar operaciones |

> Este documento define **qué**, **por qué** y **en qué orden**. Cada fase requiere aprobación explícita antes de ejecutar cambios en DEV.

---

## Principios de implementación Enterprise (nivel mundial)

1. **Decisión justificada** — Toda configuración lleva razón de negocio + razón técnica Odoo.
2. **Estándar antes que custom** — Usar módulos oficiales; custom solo para brecha demostrada.
3. **Localización oficial RD** — Stack `l10n_do*`; no soluciones OCA/terceros para fiscal.
4. **Una fuente de verdad** — Maestros (productos, partners, cuentas) definidos una vez, reutilizados en Ventas, Compras, Inventario y POS.
5. **Trazabilidad fiscal** — Cada flujo comercial debe cerrar en contabilidad RD (ITBIS, NCF tradicional en Etapa 1).
6. **Preparación go-live** — DEV es laboratorio; diseño asumiendo promoción DEV → TEST → PROD.
7. **No asumir documentación** — Especialmente localización RD: citar fuente oficial o evidencia en código desplegado.

---

## Infraestructura congelada

**No modificar** salvo error crítico que impida operar DEV:

| Componente | Estado |
|------------|--------|
| Docker / Compose DEV | 🔒 Congelado |
| Traefik | 🔒 Congelado |
| PostgreSQL | 🔒 Congelado |
| Imagen `hellenia-odoo:19-enterprise` | 🔒 Congelado |
| Código Enterprise en imagen | 🔒 Congelado |
| Scripts backup / restore | 🔒 Congelado |
| Repo Git / despliegue infra | 🔒 Congelado |
| TEST (`test.hellenia.cloud`) | 🔒 Sin tocar |
| PROD (`odoo-pecv`, Odoo 18) | 🔒 Sin tocar |

**Permitido en fase funcional:** configuración dentro de Odoo (UI), datos maestros, instalación de módulos de aplicación vía Apps/CLI **sin** cambiar imagen Docker.

---

## Línea base técnica (DEV — verificado 2026-06-30)

| Elemento | Valor |
|----------|-------|
| Odoo | `19.0+e-20260619` |
| Imagen | `hellenia-odoo:19-enterprise` |
| `web_enterprise` | Instalado |
| Licencia registrada | No |
| BD | `hellenia_dev` |
| Módulos RD en imagen | `l10n_do`, `l10n_do_reports`, `l10n_do_check_printing` |
| `l10n_do_edi` | **Ausente** en paquete `19.0+e.20260629` |

---

## Mapa de fases

```
FASE 1   Empresa ─────────────────────────────────────────────┐
FASE 2   Localización RD (NCF tradicional) ───────────────────┤
FASE 3   Contabilidad Dominicana + NCF ───────────────────────┼──► FASE 8 Reportes
FASE 4   Inventario ──────────────────────────────────────────┤         ▲
FASE 5   Compras ─────────────────────────────────────────────┤         │
FASE 6   Ventas ──────────────────────────────────────────────┤         │
FASE 7   POS ─────────────────────────────────────────────────┘         │
FASE 9   Customización (análisis) ──────────────────────────────────────┘

FASE FUTURA (independiente) ──► eNCF / l10n_do_edi / Infile / DGII electrónico
```

| Fase | Nombre | Dependencias | Entregable principal |
|------|--------|--------------|----------------------|
| **1** | Configuración General (Empresa) | — | Empresa y maestros transversales |
| **2** | Localización RD — NCF tradicional | Fase 1 | `l10n_do` + `l10n_do_reports` validados |
| **3** | Contabilidad Dominicana + NCF | Fases 1–2 | Plan, impuestos, diarios, rangos NCF |
| **4** | Inventario | Fases 1, 3 | Almacenes, rutas, valorización |
| **5** | Compras | Fases 1, 3, 4 | Ciclo de abastecimiento |
| **6** | Ventas | Fases 1, 3, 4 | Ciclo comercial con NCF B01/B02 |
| **7** | POS | Fases 1, 3, 4, 6 | Flujo tienda Hellenia (B02) |
| **8** | Reportes Gerenciales | Fases 3–7 | KPIs, tableros y reportes fiscales |
| **9** | Customización | Fases 1–8 | Mapa de brechas vs estándar |
| **Futura** | eNCF (independiente) | Go-live + upgrade | `l10n_do_edi`, Infile, DGII |

---

# FASE 1 — Configuración General

## Objetivo de negocio

Establecer la identidad legal y operativa de Hellenia en Odoo para que todos los documentos, impuestos y reportes hereden datos correctos desde el primer día.

## Objetivo técnico

Completar `res.company`, localización regional y maestros financieros base sin instalar aún apps verticales innecesarias.

## Alcance detallado

| Área | Configuración | Justificación negocio | Justificación técnica Odoo |
|------|---------------|----------------------|---------------------------|
| **Empresa** | Razón social legal, nombre comercial, logo | Identidad en facturas, POS, reportes | `res.company` es raíz de fiscalidad y documentos |
| **País** | República Dominicana | Obligatorio DGII / ITBIS | Dispara auto-instalación paquete fiscal |
| **Moneda** | DOP (RD$) principal | Operación local | Moneda compañía en todos los asientos |
| **Idioma** | Español (DO) | Usuarios y clientes RD | Traducciones `es_DO` / `es` |
| **Zona horaria** | `America/Santo_Domingo` | Cortes diarios, POS, cierres | Coherencia timestamps y cron |
| **RNC** | Registro Nacional del Contribuyente | Obligatorio facturación B2B y maestro fiscal | Campo requerido en doc. oficial RD (saas-19.3) |
| **Datos fiscales** | Dirección fiscal completa, actividad económica | Validación DGII, contratos | Contacto empresa = emisor fiscal |
| **Bancos** | Cuentas bancarias empresa (sin sync live inicial) | Pagos, conciliación futura | `res.partner.bank` en compañía |
| **Diarios** | Banco, efectivo, ventas, compras (borrador) | Separación flujos contables | Base antes de localización RD |
| **Métodos de pago** | Efectivo, transferencia, tarjeta (maestros) | POS y facturación | `account.payment.method` |

## Evidencia / referencia

- [Fiscal localizations — Odoo 19](https://www.odoo.com/documentation/19.0/applications/finance/fiscal_localizations.html) — RD en lista de países con localización.
- [Dominican Republic — Odoo saas-19.3](https://www.odoo.com/documentation/saas-19.3/applications/finance/fiscal_localizations/dominican_republic.html) — campos obligatorios empresa (RNC, dirección).

## Entregables

- [ ] Ficha empresa completada en DEV
- [ ] Checklist campos obligatorios RD
- [ ] Captura/documentación valores maestros (sin secretos en Git)
- [ ] Backup DEV post-configuración

## Criterios de aceptación

- País = DO, moneda = DOP, timezone correcta
- RNC cargado y visible en ficha empresa
- Diarios base creados (aún sin rangos NCF)

## Fuera de alcance Fase 1

- Instalación `l10n_do` (Fase 2)
- Usuarios operativos masivos (solo admin laboratorio)
- Sincronización bancaria producción

---

# FASE 2 — Localización Dominicana (NCF tradicional)

## Objetivo

Confirmar con **evidencia** el stack fiscal RD para **NCF tradicional** en Odoo 19 on-premise. **Sin eNCF, sin Infile, sin `l10n_do_edi`.**

## Decisión de alcance (aprobada)

| Componente | Etapa 1 | Justificación |
|------------|---------|---------------|
| `l10n_do` | ✅ Instalar | Doc oficial: *"minimum configuration required... according to DGII guidelines"* |
| `l10n_do_reports` | ✅ Instalar | Reportes regulatorios RD |
| `l10n_do_edi` | ❌ **No instalar** | Exclusivo eNCF/Infile — fuera de alcance |
| Infile / DGII electrónico | ❌ **No configurar** | Fase Futura independiente |

Ver análisis completo: [NCF_IMPLEMENTATION.md](NCF_IMPLEMENTATION.md)

## 2.1 Evidencia documental oficial

### A. Odoo 19.0 (documentación fija del proyecto)

| Fuente | Hallazgo |
|--------|----------|
| [Fiscal localizations 19.0](https://www.odoo.com/documentation/19.0/applications/finance/fiscal_localizations.html) | **República Dominicana** listada como país con localización fiscal |
| URL `.../fiscal_localizations/dominican_republic.html` en rama **19.0** | **404** — detalle RD no publicado en 19.0 |
| [Electronic invoicing (EDI) 19.0](https://www.odoo.com/documentation/19.0/applications/finance/accounting/customer_invoices/electronic_invoicing.html) | EDI genérico — **no aplica** a Etapa 1 |

### B. Documentación Odoo saas-19.3 / master (referencia funcional)

Fuente: [Dominican Republic — saas-19.3](https://www.odoo.com/documentation/saas-19.3/applications/finance/fiscal_localizations/dominican_republic.html)

| Nombre | Módulo | Etapa 1 | Descripción oficial |
|--------|--------|---------|---------------------|
| Dominican Republic - Accounting | `l10n_do` | ✅ Core | Plan, impuestos, configuración mínima DGII |
| Dominican Republic - Accounting Reports | `l10n_do_reports` | ✅ Manual/auto | Reportes regulatorios RD |
| Dominican Republic - Accounting EDI | `l10n_do_edi` | ❌ Excluido | ECF, eNCF, Infile → DGII |
| Dominican Republic - Checks Layout | `l10n_do_check_printing` | ⚠️ Opcional | Cheques bancarios RD |

Cita oficial: *"The localization's **core modules** are installed automatically... **The rest can be manually installed.**"*  
→ `l10n_do_edi` **no es core**; es módulo adicional para facturación electrónica.

### C. Evidencia en código desplegado Hellenia (19.0+e.20260629)

| Módulo | Presente | Versión | Rol Etapa 1 |
|--------|----------|---------|-------------|
| `l10n_do` | ✅ | 2.0 | Base NCF tradicional, ITBIS, retenciones |
| `l10n_do_reports` | ✅ | 1.0 | Reportes fiscales |
| `l10n_do_check_printing` | ✅ | 1.0 | Opcional |
| `l10n_do_edi` | ❌ Ausente | — | **No requerido** para NCF tradicional |

Manifest `l10n_do` declara secuencias NCF: B01 valor fiscal, B02 consumo, ND/NC, informales, gastos menores, gubernamentales.

**Advertencia manifest 19.0:** texto legacy indica que secuencias NCF podrían requerir terceros — **validar en DEV** durante Fase 2–3.

### D. Módulos adicionales oficiales (no fiscal, requeridos por cadena)

| Módulo | Rol | Instalación |
|--------|-----|-------------|
| `account` | Contabilidad base | Core |
| `account_accountant` | Suite EE | Fase 3 |
| `account_reports` | Motor reportes | Prerrequisito `l10n_do_reports` |

**No se requiere ningún otro módulo oficial** para NCF tradicional además de `l10n_do` + `l10n_do_reports` (+ suite contable EE).

## 2.2 Confirmación: suficiencia para NCF tradicional

| Pregunta | Respuesta con evidencia |
|----------|------------------------|
| ¿`l10n_do` + `l10n_do_reports` bastan? | **Sí** — doc oficial separa base DGII (`l10n_do`) de eNCF (`l10n_do_edi`) |
| ¿Instalar `l10n_do_edi`? | **No** — explícitamente fuera de alcance Etapa 1 |
| ¿Módulo equivalente a `l10n_do`? | **No** — nombre técnico estable |
| ¿eNCF absorbido en `l10n_do`? | **No** — módulo separado en documentación oficial |

## 2.4 Decisión Fase 2 (Hellenia)

| Acción | Decisión |
|--------|----------|
| Instalar `l10n_do` | ✅ Sí |
| Instalar `l10n_do_reports` | ✅ Sí |
| Instalar `l10n_do_check_printing` | ⚠️ Solo si usan cheques |
| Instalar `l10n_do_edi` | ❌ **Prohibido en Etapa 1** |
| Configurar Infile | ❌ **Prohibido en Etapa 1** |

## Entregables Fase 2

- [ ] `l10n_do` + `l10n_do_reports` instalados en DEV
- [ ] Confirmación `l10n_do_edi` **no** instalado
- [ ] Validación impuestos ITBIS en UI
- [ ] Acta evidencia archivada — ver [NCF_IMPLEMENTATION.md](NCF_IMPLEMENTATION.md)

---

# FASE 3 — Contabilidad Dominicana + NCF tradicional

## Objetivo de negocio

Operar contabilidad alineada a DGII/NIIF con NCF tradicional, ITBIS, retenciones y trazabilidad fiscal completa.

## Objetivo técnico

Parametrizar plan contable, impuestos, diarios, rangos NCF y cuentas tras instalar `l10n_do`. Ver detalle en [NCF_IMPLEMENTATION.md](NCF_IMPLEMENTATION.md).

## Alcance

| Componente | Acciones | Justificación |
|------------|----------|---------------|
| **Plan contable** | Revisar/ajustar cuentas post `l10n_do` | Base DGII/NIIF precargada |
| **Impuestos ITBIS** | Activar tasas 18%, 16%, 0%, exento | Doc oficial saas-19.3 |
| **Retenciones** | ISR, ITBIS retenido según operación | Cumplimiento proveedores/servicios |
| **Propina 10%** | Activar si aplica rubro Hellenia | Solo hospitalidad si aplica |
| **Diarios** | Ventas, compras, banco, efectivo | Separación auditoría |
| **Diarios con documentos** | `Use Documents` en ventas/compras | Obligatorio NCF tradicional |
| **Rangos NCF** | Configurar rangos DGII por tipo (B01, B02…) | Autorización gubernamental |
| **Cuentas bancarias** | Vincular diarios banco | Conciliación |
| **Configuración fiscal** | Posiciones fiscales, grupos impuestos | Automatización impuestos |
| **Suite EE** | `account_accountant`, `account_reports` | Cierre, informes |

## Dependencias

- Fase 1 completa
- Fase 2: `l10n_do` + `l10n_do_reports` instalados

## Entregables

- [ ] Plan de cuentas validado con contador Hellenia
- [ ] Matriz impuestos (venta/compra/servicios)
- [ ] Diarios operativos con `Use Documents`
- [ ] Rangos NCF B01/B02 (mínimo) configurados
- [ ] Factura prueba B02 con NCF asignado
- [ ] Asiento de apertura (si aplica migración)

## Fuera de alcance

- eNCF, `l10n_do_edi`, Infile, DGII electrónico
- Conciliación bancaria automática live

---

# FASE 4 — Inventario

## Objetivo de negocio

Controlar stock, costos y disponibilidad para ventas, compras y POS con un solo inventario veraz.

## Diseño propuesto

| Elemento | Diseño Hellenia | Justificación |
|----------|-----------------|---------------|
| **Almacenes** | Central + tiendas/POS si multi-sucursal | Visibilidad por ubicación |
| **Ubicaciones** | Entrada, stock, salida, cuarentena, devoluciones | Trazabilidad operativa |
| **Rutas** | Comprar → recibir; Pick → ship; POS consumo | Flujos estándar Odoo |
| **Categorías** | Jerarquía por línea de negocio Hellenia | Políticas contables por categoría |
| **Atributos** | Talla, color, etc. (si retail) | Variantes producto |
| **UdM** | Unidad, caja, peso según rubro | Compras vs ventas |
| **Valorización** | FIFO o costo promedio (decisión financiera) | Impacto margen y DGII |
| **Códigos barras** | EAN interno + `stock_barcode` (EE) si volumen | Eficiencia almacén |
| **Lotes/series** | Si regulación o garantía lo exige | Trazabilidad |

## Dependencias

- Fase 3 (cuentas stock, valorización)
- Productos maestros definidos

## Entregables

- [ ] Mapa almacenes/ubicaciones
- [ ] Política valorización documentada
- [ ] Catálogo productos piloto (10–20 SKUs)
- [ ] Prueba recepción → entrega interna

---

# FASE 5 — Compras

## Objetivo de negocio

Abastecimiento controlado: solicitud → orden → recepción → factura proveedor con retenciones y NCF de entrada.

## Configuración

| Área | Configuración | Justificación |
|------|---------------|---------------|
| **RFQ** | Comparación proveedores | Mejor precio/plazo |
| **Órdenes** | Aprobaciones (`approvals` EE opcional) | Control gasto |
| **Recepción** | 1-step / 2-step según almacén | Operación real |
| **Proveedores** | RNC, términos, moneda | Fiscal RD |
| **Retenciones** | En facturas servicios/bienes | DGII |
| **NCF compra** | B11 informales, B13 gastos menores si aplica | Tipos entrada |
| **Políticas** | Cantidad mínima, lead times | Reposición |

## Dependencias

- Fases 3–4
- Catálogo proveedores

## Entregables

- [ ] PO → recepción → vendor bill probado
- [ ] Retención aplicada en caso de prueba
- [ ] Integración con reglas de reorden (si aplica)

---

# FASE 6 — Ventas

## Objetivo de negocio

Ciclo comercial completo: cotización → pedido → entrega → factura fiscal RD con NCF tradicional.

## Configuración

| Área | Configuración | Justificación |
|------|---------------|---------------|
| **Cotizaciones** | Plantillas, validez, términos | Ventas B2B |
| **Pedidos** | Confirmación, política entrega | Compromiso stock |
| **Facturación** | Política facturar en entrega / pedido | Flujo caja vs accrual |
| **Listas de precios** | Por canal (mayorista, retail, POS) | Márgenes diferenciados |
| **Descuentos** | Línea vs global; límites por rol | Control comercial |
| **Vendedores** | Equipos comerciales, comisiones (fase 2) | CRM opcional |
| **Documentos RD** | B01 (RNC cliente) / B02 (consumo) | DGII — `l10n_do` |
| **Términos pago** | Contado, crédito 30/60 | Cobranza |

## Dependencias

- Fases 3–4
- Partners clientes con RNC cuando B2B

## Entregables

- [ ] Flujo cotización → factura probado
- [ ] ITBIS correcto en líneas
- [ ] NCF B01 y B02 asignados correctamente
- [ ] Nota crédito B04 con referencia NCF origen

---

# FASE 7 — POS (Punto de venta)

## Objetivo de negocio

Diseñar el flujo completo de tienda Hellenia: venta rápida, ITBIS, medios de pago, cierre de caja, integración inventario y contabilidad.

## Diseño funcional propuesto

```
Apertura caja → Venta POS → Pago → Ticket/Factura consumo
      → Inventario (ubicación tienda) → Asiento contable
      → Cierre sesión → Conciliación efectivo/tarjeta
```

| Componente | Diseño | Justificación |
|------------|--------|---------------|
| **Config POS** | Tienda(s), PdV, sesiones | Multi-tienda futuro |
| **Productos** | Categorías POS, disponibles en ubicación tienda | Solo vendible si hay stock |
| **Impuestos** | ITBIS en precios tax-included o excluded (decisión) | Transparencia cliente |
| **Pagos** | Efectivo, tarjeta, transferencia | Métodos RD reales |
| **Factura fiscal** | B02 consumo (POS y retail) | DGII — NCF tradicional |
| **Propina** | Si aplica rubro | Impuesto 10% doc RD |
| **Hardware** | Impresora, cajón, escáner (inventario futuro) | Operación tienda |
| **Contabilidad** | Diarios POS, cuenta transitoria | Cierre automático |
| **Inventario** | Ruta POS → almacén tienda | Stock en tiempo real |

## Dependencias

- Fases 3, 4, 6
- Productos y listas de precios retail

## Entregables

- [ ] Documento flujo POS Hellenia (diagrama + roles)
- [ ] Config POS piloto en DEV
- [ ] Sesión de prueba con cierre
- [ ] Checklist hardware go-live

---

# FASE 8 — Reportes Gerenciales

## Objetivo

Definir KPIs y tableros para dirección Hellenia — no solo reportes contables RD.

## KPIs propuestos

### Financieros

| KPI | Fuente Odoo | Decisión que habilita |
|-----|-------------|----------------------|
| Ingresos netos período | Contabilidad / `account_reports` | Desempeño comercial |
| Margen bruto % | Ventas − costo ventas | Pricing y mix |
| EBITDA aproximado | Cuentas gestión | Eficiencia operativa |
| Cuentas por cobrar aging | Partner ledger | Cobranza |
| Cuentas por pagar aging | Partner ledger | Tesorería |
| ITBIS débito/crédito | Tax report RD | Preparación declaración |
| Flujo caja indirecto | Cash flow statement EE | Liquidez |

### Comerciales

| KPI | Fuente | Decisión |
|-----|--------|----------|
| Ventas por canal (POS / B2B) | Ventas analítica | Estrategia canal |
| Ticket promedio POS | POS reporting | Layout tienda / promos |
| Top productos / categorías | Ventas por producto | Compras |
| Tasa conversión cotización | CRM/Sales | Equipo comercial |
| Descuento promedio % | Líneas factura | Política precios |

### Inventario

| KPI | Fuente | Decisión |
|-----|--------|----------|
| Rotación inventario | Stock / COGS | Capital de trabajo |
| Días de stock | Stock valorizado | Reposición |
| Quiebres de stock | Moves / reglas | SLA clientes |
| Exactitud inventario | Ajustes vs teórico | Procesos almacén |
| Valor inventario | Stock valuation | Balance |

### Compras

| KPI | Fuente | Decisión |
|-----|--------|----------|
| Lead time proveedor | PO → recepción | Negociación |
| Compras por proveedor | Vendor bills | Concentración riesgo |
| Variación precio compra | Histórico PO | Renegociación |

### POS / Tienda

| KPI | Fuente | Decisión |
|-----|--------|----------|
| Ventas por sesión/cajero | POS sessions | Control interno |
| Diferencia cierre caja | Sesión POS | Fraude/errores |
| Mix de pago efectivo vs tarjeta | Pagos POS | Comisiones bancarias |

### Fiscal RD (cuando `l10n_do_reports` activo)

| KPI / Reporte | Fuente | Decisión |
|---------------|--------|----------|
| Libro ventas/compras | `l10n_do_reports` | Cierre fiscal |
| Declaración ITBIS | Tax report | Cumplimiento DGII |
| Retenciones emitidas/recibidas | Contabilidad RD | Declaraciones |

## Herramientas Odoo

| Herramienta | Uso |
|-------------|-----|
| `account_reports` / EE | Financieros |
| `spreadsheet_edition` | Tableros ad-hoc |
| Vistas pivot/graph estándar | Operativos |
| `hellenia_reports` (futuro custom) | Solo brechas no cubiertas |

## Entregables

- [ ] Catálogo KPI aprobado por dirección
- [ ] Tablero mínimo viable en DEV
- [ ] Mapeo KPI → menú Odoo

---

# FASE 9 — Customización (solo análisis)

## Objetivo

Identificar qué requiere desarrollo propio vs configuración estándar. **No desarrollar en esta fase.**

## Matriz estándar vs custom

| Necesidad | Estándar Odoo | ¿Custom? | Módulo propuesto |
|-----------|---------------|----------|------------------|
| Config base Hellenia (secuencias, parámetros) | Parcial (`res.config.settings`) | ⚠️ Evaluar | `hellenia_base` |
| Extensiones inventario (reglas Hellenia) | `stock`, `stock_barcode` | ⚠️ Evaluar | `hellenia_inventory` |
| Extensiones contables RD | `l10n_do*` | ⚠️ Solo si brecha fiscal | `hellenia_account` |
| Reportes dirección no en `l10n_do_reports` | `account_reports`, spreadsheet | ⚠️ Evaluar | `hellenia_reports` |
| Flujos POS específicos | `point_of_sale` | ⚠️ Evaluar | `hellenia_pos` |
| Utilidades compartidas Justech | — | ✅ Probable | `justech_core` |
| eNCF / Infile | Fase Futura — estándar Odoo `l10n_do_edi` | ❌ Fuera Etapa 1 | — |
| Integraciones externas (ERP legado, e-commerce) | Conectores estándar / API | 📋 Por definir | TBD |

## Criterios para aprobar custom

1. Requisito documentado que **no** se resuelve con configuración estándar.
2. Alternativa estándar descartada por escrito.
3. Herencia `_inherit` — nunca parche en `enterprise/`.
4. ROI operativo claro (horas ahorradas / riesgo reducido).

## Entregables

- [ ] Registro de brechas (issue log funcional)
- [ ] Priorización MoSCoW custom
- [ ] Estimación por módulo (fase posterior)

---

# FASE FUTURA — eNCF (independiente de Etapa 1)

> **No ejecutar.** Documentación de referencia para cuando dirección active facturación electrónica.

| Componente | Acción futura |
|------------|---------------|
| `l10n_do_edi` | Instalar cuando disponible en build on-premise estable |
| Infile | Contrato + credenciales Test → Prod |
| DGII | Registro emisor electrónico + rangos E31–E34 |
| Upgrade Odoo | Posible 19.3+ si `l10n_do_edi` no en 19.0 |

Referencias: [NCF_IMPLEMENTATION.md](NCF_IMPLEMENTATION.md) § Preparación futura, [INFILE-REQUIREMENTS.md](INFILE-REQUIREMENTS.md)

---

## Gobernanza y aprobaciones

| Gate | Aprobación requerida | Ambiente |
|------|---------------------|----------|
| Inicio Fase N | Usuario confirma *"Aprobado Fase N"* | DEV |
| Instalación módulos app | Por fase | DEV |
| Datos maestros productivos | Usuario Hellenia valida | DEV |
| Registro licencia | Diferido — go-live PROD | PROD futura |
| Promoción TEST | Duplicar + neutralize | Post-validación DEV |

## Riesgos transversales (Etapa 1)

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Manifest legacy NCF en `l10n_do` 19.0 | Secuencias podrían no operar sin validación | Prueba obligatoria Fase 2–3 en DEV |
| Trial Enterprise sin registro | Expiración BD | Monitorear `database.expiration_date` |
| Documentación 19.0 incompleta RD | Decisiones incorrectas | Evidencia saas-19.3 + manifests + [NCF_IMPLEMENTATION.md](NCF_IMPLEMENTATION.md) |
| Configurar sin dueño negocio | Re-trabajo | Checklist aprobación por fase |
| Detalle reportes `l10n_do_reports` no publicado | Incertidumbre 606/607/608 | Validar menú tras instalar con contador |
| Plazos Ley 32-23 e-CF | Migración obligatoria futura | Fase Futura eNCF planificada, no bloquea Etapa 1 |

---

## Próximo paso recomendado

**Aprobación para ejecutar Fase 1** en DEV:

> *"Aprobado Fase 1 — Configuración General"*

Hasta entonces: solo planificación (este documento).

---

## Referencias

| Documento | Uso |
|-----------|-----|
| [NCF_IMPLEMENTATION.md](NCF_IMPLEMENTATION.md) | **Guía NCF tradicional Etapa 1** |
| [UNREGISTERED_ENTERPRISE_LIMITATIONS.md](UNREGISTERED_ENTERPRISE_LIMITATIONS.md) | Alcance sin licencia |
| [L10N-RD-READINESS.md](L10N-RD-READINESS.md) | Stack RD |
| [INFILE-REQUIREMENTS.md](INFILE-REQUIREMENTS.md) | eNCF — solo Fase Futura |
| [ENTERPRISE-LICENSING.md](ENTERPRISE-LICENSING.md) | Política licencia go-live |
| [CUSTOM_MODULE_GUIDE.md](CUSTOM_MODULE_GUIDE.md) | Estándares custom |
| [Odoo 19 Fiscal localizations](https://www.odoo.com/documentation/19.0/applications/finance/fiscal_localizations.html) | Lista países |
| [Odoo saas-19.3 Dominican Republic](https://www.odoo.com/documentation/saas-19.3/applications/finance/fiscal_localizations/dominican_republic.html) | Detalle módulos RD |

---

**Versión:** 2.0  
**Mantenido por:** Consultoría implementación Justech  
**Infraestructura:** 🔒 Congelada  
**Alcance Etapa 1:** NCF tradicional — sin eNCF
