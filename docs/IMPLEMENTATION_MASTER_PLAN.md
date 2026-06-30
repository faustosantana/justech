# Plan Maestro de Implementación — Hellenia Odoo Enterprise 19

**Rol:** Consultor Senior de Implementación Odoo Enterprise  
**Cliente:** Hellenia, S.R.L. — República Dominicana  
**Ambiente de trabajo:** `hellenia_dev` (DEV laboratorio)  
**Fecha:** 2026-06-30  
**Estado:** Fase funcional iniciada — **sin ejecución de configuración aún**

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
5. **Trazabilidad fiscal** — Cada flujo comercial debe poder cerrar en contabilidad RD (ITBIS, NCF/eNCF cuando aplique).
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
FASE 1  Configuración General ──────┐
FASE 2  Localización RD ────────────┤
FASE 3  Contabilidad ───────────────┼──► FASE 8 Reportes Gerenciales
FASE 4  Inventario ─────────────────┤         ▲
FASE 5  Ventas ─────────────────────┤         │
FASE 6  Compras ────────────────────┤         │
FASE 7  POS ────────────────────────┘         │
FASE 9  Customización (análisis) ─────────────┘
```

| Fase | Nombre | Dependencias | Entregable principal |
|------|--------|--------------|----------------------|
| **1** | Configuración General | — | Empresa y maestros transversales |
| **2** | Localización Dominicana | Fase 1 | Stack RD validado con evidencia |
| **3** | Contabilidad | Fases 1–2 | Plan contable, impuestos, diarios |
| **4** | Inventario | Fases 1, 3 | Almacenes, rutas, valorización |
| **5** | Ventas | Fases 1, 3, 4 | Ciclo comercial completo |
| **6** | Compras | Fases 1, 3, 4 | Ciclo de abastecimiento |
| **7** | POS | Fases 1, 3, 4, 5 | Flujo tienda Hellenia |
| **8** | Reportes Gerenciales | Fases 3–7 | KPIs y tableros |
| **9** | Customización | Fases 1–8 | Mapa de brechas vs estándar |

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
| **RNC** | Registro Nacional del Contribuyente | Obligatorio ECF / facturación B2B | Campo requerido en doc. oficial RD (saas-19.3) |
| **Datos fiscales** | Dirección fiscal completa, actividad económica | Validación DGII, contratos | Contacto empresa = emisor ECF |
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

# FASE 2 — Localización Dominicana

## Objetivo

Confirmar con **evidencia** el stack fiscal RD aplicable a Hellenia en Odoo 19 on-premise **sin asumir** nombres de módulos ni disponibilidad de eNCF.

## 2.1 Evidencia documental oficial

### A. Odoo 19.0 (documentación fija del proyecto)

| Fuente | Hallazgo |
|--------|----------|
| [Fiscal localizations 19.0](https://www.odoo.com/documentation/19.0/applications/finance/fiscal_localizations.html) | **República Dominicana** listada como país con módulos de localización fiscal |
| URL `.../fiscal_localizations/dominican_republic.html` en rama **19.0** | **404 — página no publicada** en documentación 19.0 al 2026-06-30 |
| [Electronic invoicing (EDI) 19.0](https://www.odoo.com/documentation/19.0/applications/finance/accounting/customer_invoices/electronic_invoicing.html) | EDI genérico; remite a páginas por país — **sin detalle RD en 19.0** |

### B. Documentación Odoo más reciente (referencia funcional — saas-19.3 / master)

> **Nota metodológica:** Odoo publica el detalle RD en ramas `saas-19.3` y `master`. No asumimos paridad 1:1 con on-premise `19.0+e.20260629` sin verificar en código desplegado.

Fuente: [Dominican Republic — saas-19.3](https://www.odoo.com/documentation/saas-19.3/applications/finance/fiscal_localizations/dominican_republic.html)

| Nombre | Módulo técnico | Edición | Descripción oficial |
|--------|----------------|---------|---------------------|
| Dominican Republic - Accounting | `l10n_do` | Paquete base localización | Contabilidad mínima DGII; plan e impuestos |
| Dominican Republic - Accounting EDI | `l10n_do_edi` | Enterprise | ECF, eNCF, XML, firma, integración **Infile** → DGII |
| Dominican Republic - Accounting Reports | `l10n_do_reports` | Enterprise | Reportes regulatorios RD |
| Dominican Republic - Checks Layout | `l10n_do_check_printing` | Enterprise | Formato cheques bancarios RD |

Cita oficial módulos core: *"installed automatically with the localization. The rest can be manually installed."*

### C. Foro oficial Odoo (evidencia versión `l10n_do_edi`)

Fuente: [Forum — l10n_do documentos soportados](https://www.odoo.com/forum/help-1/l10n-do-documentos-soportados-nueva-localizacion-republica-dominicana-302531)

| Afirmación oficial (equipo/foro Odoo) | Implicación Hellenia |
|---------------------------------------|---------------------|
| Localización RD anunciada para **19.3 (SaaS)** | Roadmap Odoo priorizó SaaS para eNCF completo |
| *"l10n_do_edi ... estará disponible de versión 19.3 en adelante"* | **No asumir** eNCF en build on-premise `19.0+e.20260629` |
| Documentos E31–E34 documentados | Objetivo fiscal go-live; planificar upgrade o tarball posterior |

### D. Evidencia en código desplegado Hellenia (on-premise 19.0+e.20260629)

| Módulo | Presente en imagen DEV | Manifest (versión) | `depends` |
|--------|------------------------|-------------------|-----------|
| `l10n_do` | ✅ Community | 2.0 | `account`, `base_iban` |
| `l10n_do_reports` | ✅ Enterprise | 1.0 | `l10n_do`, `account_reports` — `auto_install: True` |
| `l10n_do_check_printing` | ✅ Enterprise | 1.0 | `account_check_printing`, `l10n_do` — `auto_install: ['l10n_do']` |
| `l10n_do_edi` | ❌ **Ausente** | — | — |

Descripción manifest `l10n_do` (código): catálogo cuentas DGII/NIIF, impuestos, compatibilidad internacionalización.

## 2.2 Funcionalidades por módulo (según documentación saas-19.3)

### `l10n_do` (base — disponible en Hellenia)

| Funcionalidad | Evidencia |
|---------------|-----------|
| Plan de cuentas RD | Doc saas-19.3 § Chart of accounts |
| ITBIS 18%, 16%, 0%, exento | Doc saas-19.3 § Taxes |
| Retenciones ITBIS / ISR | Doc saas-19.3 § Taxes |
| Propina 10% | Doc saas-19.3 § Taxes |
| Multi-moneda (DOP + extranjeras) | Doc saas-19.3 § Multi-currency |
| NCF / documentos fiscales (no electrónicos) | Manifest + práctica localización |

### `l10n_do_reports` (disponible en Hellenia)

| Funcionalidad | Evidencia |
|---------------|-----------|
| Reportes financieros regulatorios RD | Doc saas-19.3: *"financial reports tailored to the Dominican Republic's regulatory requirements"* |
| Detalle línea por línea de cada reporte | **No especificado** en documentación pública — validar en UI tras instalar |

### `l10n_do_edi` (NO disponible en build actual)

| Funcionalidad | Estado Hellenia |
|---------------|-----------------|
| E31–E34 eNCF | ⏳ Requiere módulo + Infile + DGII |
| Integración Infile | Documentada solo con `l10n_do_edi` |
| Ambientes Demo/Test/Prod | Doc saas-19.3 § Configuration |

### `l10n_do_check_printing` (disponible — opcional)

| Funcionalidad | Cuándo usar |
|---------------|-------------|
| Impresión cheques formato RD | Si Hellenia paga proveedores con cheques pre-impresos |

## 2.3 Módulos equivalentes / cambios de nombre

| Pregunta | Respuesta basada en evidencia |
|----------|------------------------------|
| ¿Otro nombre para `l10n_do`? | **No** — nombre técnico estable en doc y código |
| ¿`l10n_do_edi` absorbido en `l10n_do`? | **No** — sigue siendo módulo separado en doc saas-19.3 |
| ¿eNCF dentro de `account_edi` genérico? | RD usa módulo país `l10n_do_edi` + Infile, no Peppol |
| ¿`account_accountant` reemplaza contabilidad? | En manifest 19.0 se muestra como **"Invoicing"** (EE) — suite contable avanzada, complementa `account` |

## 2.4 Decisión recomendada Fase 2 (Hellenia)

| Acción | Decisión | Justificación |
|--------|----------|---------------|
| Instalar `l10n_do` | ✅ Sí | Disponible; base obligatoria RD |
| Instalar `l10n_do_reports` | ✅ Sí | Disponible; auto_install tras `l10n_do` + `account_reports` |
| Instalar `l10n_do_check_printing` | ⚠️ Condicional | Solo si Hellenia usa cheques |
| Instalar `l10n_do_edi` | ❌ No ahora | **Módulo ausente** en 19.0+e.20260629 |
| Plan eNCF go-live | 📋 Documentar | Upgrade 19.3+ o nuevo tarball Enterprise cuando Odoo publique on-premise |

## Entregables Fase 2

- [ ] Acta de evidencia (este § archivado tras ejecución)
- [ ] `l10n_do` + `account_reports` / suite contable EE instalados
- [ ] Validación impuestos ITBIS en UI
- [ ] Gap analysis formal `l10n_do_edi` para steering committee

---

# FASE 3 — Contabilidad

## Objetivo de negocio

Operar contabilidad alineada a DGII/NIIF con trazabilidad de ITBIS, retenciones y documentos fiscales.

## Objetivo técnico

Activar suite contable Enterprise y parametrizar plan, impuestos, diarios y cuentas tras `l10n_do`.

## Alcance

| Componente | Acciones | Justificación |
|------------|----------|---------------|
| **Plan contable** | Revisar/ajustar cuentas post `l10n_do` | Base DGII/NIIF precargada — evitar reinventar |
| **Impuestos ITBIS** | Activar tasas 18%, 16%, 0%, exento | Doc oficial saas-19.3 |
| **Retenciones** | ISR, ITBIS retenido según operación | Cumplimiento proveedores/servicios |
| **Propina 10%** | Activar si aplica restaurante/hospitalidad | Solo si Hellenia tiene ese rubro |
| **Diarios** | Ventas, compras, banco, efectivo, misc | Separación auditoría |
| **Diarios con documentos** | `Use Documents` en ventas (prep. eNCF) | Requisito doc RD para EDI futuro |
| **Cuentas bancarias** | Vincular diarios banco | Conciliación |
| **Configuración fiscal** | Posiciones fiscales, grupos impuestos | Ventas/exportación si aplica |
| **Suite EE** | `account_accountant`, reportes | Cierre, informes, seguimiento |

## Dependencias

- Fase 1 completa
- Fase 2: `l10n_do` instalado

## Entregables

- [ ] Plan de cuentas validado con contador Hellenia
- [ ] Matriz impuestos (venta/compra/servicios)
- [ ] Diarios operativos configurados
- [ ] Asiento de apertura (si aplica migración)

## Fuera de alcance

- eNCF producción (sin `l10n_do_edi`)
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

# FASE 5 — Ventas

## Objetivo de negocio

Ciclo comercial completo: cotización → pedido → entrega → factura fiscal RD.

## Configuración

| Área | Configuración | Justificación |
|------|---------------|---------------|
| **Cotizaciones** | Plantillas, validez, términos | Ventas B2B |
| **Pedidos** | Confirmación, política entrega | Compromiso stock |
| **Facturación** | Política facturar en entrega / pedido | Flujo caja vs accrual |
| **Listas de precios** | Por canal (mayorista, retail, POS) | Márgenes diferenciados |
| **Descuentos** | Línea vs global; límites por rol | Control comercial |
| **Vendedores** | Equipos comerciales, comisiones (fase 2) | CRM opcional |
| **Documentos RD** | Tipos NCF según cliente (B01/B02…) | DGII — con `l10n_do` |
| **Términos pago** | Contado, crédito 30/60 | Cobranza |

## Dependencias

- Fases 3–4
- Partners clientes con RNC cuando B2B

## Entregables

- [ ] Flujo cotización → factura probado
- [ ] ITBIS correcto en líneas
- [ ] Secuencias NCF en diario ventas (no eNCF hasta EDI)

---

# FASE 6 — Compras

## Objetivo de negocio

Abastecimiento controlado: solicitud → orden → recepción → factura proveedor con retenciones.

## Configuración

| Área | Configuración | Justificación |
|------|---------------|---------------|
| **RFQ** | Comparación proveedores | Mejor precio/plazo |
| **Órdenes** | Aprobaciones (`approvals` EE opcional) | Control gasto |
| **Recepción** | 1-step / 2-step según almacén | Operación real |
| **Proveedores** | RNC, términos, moneda | Fiscal RD |
| **Retenciones** | En facturas servicios/bienes | DGII |
| **Políticas** | Cantidad mínima, lead times | Reposición |

## Dependencias

- Fases 3–4
- Catálogo proveedores

## Entregables

- [ ] PO → recepción → vendor bill probado
- [ ] Retención aplicada en caso de prueba
- [ ] Integración con reglas de reorden (si aplica)

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
| **Factura fiscal** | B02 consumo / E32 cuando exista EDI | DGII |
| **Propina** | Si aplica rubro | Impuesto 10% doc RD |
| **Hardware** | Impresora, cajón, escáner (inventario futuro) | Operación tienda |
| **Contabilidad** | Diarios POS, cuenta transitoria | Cierre automático |
| **Inventario** | Ruta POS → almacén tienda | Stock en tiempo real |

## Dependencias

- Fases 3, 4, 5
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
| eNCF / Infile | `l10n_do_edi` (cuando exista) | ❌ No custom | Estándar Odoo |
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

## Gobernanza y aprobaciones

| Gate | Aprobación requerida | Ambiente |
|------|---------------------|----------|
| Inicio Fase N | Usuario confirma *"Aprobado Fase N"* | DEV |
| Instalación módulos app | Por fase | DEV |
| Datos maestros productivos | Usuario Hellenia valida | DEV |
| Registro licencia | Diferido — go-live PROD | PROD futura |
| Promoción TEST | Duplicar + neutralize | Post-validación DEV |

## Riesgos transversales

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| `l10n_do_edi` ausente en 19.0 | Sin eNCF legal | Plan upgrade; operar NCF papel en lab |
| Trial Enterprise sin registro | Expiración BD | Monitorear `database.expiration_date` |
| Documentación 19.0 incompleta RD | Decisiones incorrectas | Evidencia saas-19.3 + manifests |
| Configurar sin dueño negocio | Re-trabajo | Checklist aprobación por fase |
| Mezclar datos test/prod | Legal/fiscal | Sin Infile prod en DEV |

---

## Próximo paso recomendado

**Aprobación para ejecutar Fase 1** en DEV:

> *"Aprobado Fase 1 — Configuración General"*

Hasta entonces: solo planificación (este documento).

---

## Referencias

| Documento | Uso |
|-----------|-----|
| [UNREGISTERED_ENTERPRISE_LIMITATIONS.md](UNREGISTERED_ENTERPRISE_LIMITATIONS.md) | Alcance sin licencia |
| [L10N-RD-READINESS.md](L10N-RD-READINESS.md) | Stack RD |
| [INFILE-REQUIREMENTS.md](INFILE-REQUIREMENTS.md) | eNCF futuro |
| [ENTERPRISE-LICENSING.md](ENTERPRISE-LICENSING.md) | Política licencia go-live |
| [CUSTOM_MODULE_GUIDE.md](CUSTOM_MODULE_GUIDE.md) | Estándares custom |
| [Odoo 19 Fiscal localizations](https://www.odoo.com/documentation/19.0/applications/finance/fiscal_localizations.html) | Lista países |
| [Odoo saas-19.3 Dominican Republic](https://www.odoo.com/documentation/saas-19.3/applications/finance/fiscal_localizations/dominican_republic.html) | Detalle módulos RD |

---

**Versión:** 1.0  
**Mantenido por:** Consultoría implementación Justech  
**Infraestructura:** 🔒 Congelada
