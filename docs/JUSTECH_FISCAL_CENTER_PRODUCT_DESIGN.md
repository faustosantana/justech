# JUSTECH FISCAL CENTER — Product Design Document

| Metadato | Valor |
|----------|-------|
| **Producto** | Justech Fiscal Center |
| **Código comercial** | `justech_fiscal_center` |
| **Versión del documento** | 1.0.0 |
| **Fecha** | 2026-07-09 |
| **Estado** | **Diseño aprobación pendiente** — sin implementación |
| **Plataforma** | Odoo 19 Enterprise |
| **Mercado** | República Dominicana |
| **Audiencia** | Producto, UX, Arquitectura, Implementación, Comercial |
| **Precedente** | Sprint 2 cerrado (`justech_l10n_do_ncf` 19.0.2.1.0); Gap Analysis v1.0 |

---

## Control del documento

Este PDD define **qué construiremos** cuando se reanude el desarrollo. Ninguna sección implica código, despliegue ni cambios en entornos operativos.

**Principio rector del producto:**

> Proteger la información antes que desarrollar funcionalidades — y hacer que proteger sea **visible, medible y accionable** para cada rol.

---

# 1. Visión del producto

## 1.1 ¿Qué es Justech Fiscal Center?

**Justech Fiscal Center** es el producto fiscal oficial de Justech para Odoo en República Dominicana: un **centro de control enterprise** que unifica configuración, operación, cumplimiento DGII, diagnóstico, reportes y evolución hacia comprobantes electrónicos — sin obligar al usuario a entender la arquitectura interna de módulos.

No es un módulo NCF. No es un parche de localización. Es la **capa de producto** que el cliente compra, instala y opera durante años.

El NCF (serie B), los reportes DGII, los pagos con retenciones, la integración e-CF y los servicios DGII en línea son **componentes** del Fiscal Center, no productos separados que el cliente deba descubrir en menús de contabilidad.

## 1.2 ¿Por qué existe?

Porque el mercado dominicano de Odoo opera hoy con soluciones fragmentadas:

- Localizaciones que resuelven **solo** la factura, no el cierre fiscal.
- Reportes DGII desconectados de la operación diaria.
- Cero visibilidad ejecutiva sobre riesgo fiscal hasta que algo falla al publicar o exportar.
- Migraciones traumáticas entre proveedores que ponen en riesgo histórico contable.
- e-CF tratado como un add-on tardío en lugar de una evolución planificada del mismo producto.

Justech Fiscal Center existe para que **una sola instalación** entregue confianza fiscal de punta a punta: desde que el vendedor confirma una cotización hasta que el gerente ve que el mes está listo para DGII.

## 1.3 ¿Qué problema resuelve?

| Problema del mercado | Respuesta del Fiscal Center |
|----------------------|----------------------------|
| “No sé si estamos bien fiscalmente” | **Salud Fiscal** — indicador único, explicable, accionable |
| “La factura tiene demasiados campos” | **Modo Operativo** — fiscal invisible hasta que importa |
| “Perdimos un NCF / hay duplicados” | Motor NCF con consumo auditado, diagnóstico y alertas |
| “El cierre DGII es un infierno” | Workflow revisión → aprobación → export con verificador previo |
| “Tenemos 4 empresas y no vemos nada consolidado” | Dashboard multiempresa con drill-down por compañía |
| “Migrar de Adel nos da miedo” | Asistente de migración guiado, histórico read-only, cutover por empresa |
| “e-CF llegará y no estamos listos” | Módulo e-CF dentro del mismo centro, misma navegación, misma Salud Fiscal |

## 1.4 ¿Por qué es mejor que cualquier otra alternativa?

**Versus localizaciones tipo Adel (fork operativo):**

- Arquitectura desacoplada, testeable y versionada — no monolito sin tests.
- Asignación NCF **antes** del post contable — integridad real, no hacks de estado.
- Seguridad por rol — secuencias y rangos no editables por cualquier usuario.
- Salud Fiscal y diagnóstico — el competidor no tiene centro de control.

**Versus Odoo estándar + reportes sueltos:**

- Reglas DGII dominicanas nativas (B14, RD$250k, exportaciones, retenciones).
- Workflow DGII enterprise, no export ad hoc.
- Multiempresa fiscal diseñado, no accidental.

**Versus suites ERP locales cerradas:**

- Sigue siendo Odoo — ventas, inventario, contabilidad, POS en un ecosistema.
- API y eventos para IA (JAIOS), automatización y observabilidad.
- Producto parametrizable para **cualquier** cliente RD — cero hardcode de implementación.

**Promesa comercial:**

> *“En 30 segundos sabes si tu empresa está fiscalmente sana. En 30 minutos configuras una empresa nueva. En 30 días cierras DGII con confianza.”*

---

# 2. Tipos de usuarios

El Fiscal Center implementa **experiencias por rol**, no un menú único. Cada rol tiene un *home* distinto dentro del mismo producto.

## 2.1 Matriz rol × necesidad × visibilidad

| Rol | Objetivo principal | Debe ver | No debe ver |
|-----|-------------------|----------|-------------|
| **Vendedor** | Facturar rápido sin errores | Cotización, cliente, producto, tipo comprobante sugerido, alertas bloqueantes | Rangos NCF, secuencias, 606/607, configuración empresa, void NCF, logs técnicos |
| **Cajero (POS)** | Cobrar y emitir comprobante | POS simplificado, estado NCF del ticket, alerta si secuencia agotada | Reportes DGII, administración rangos, multiempresa consolidada |
| **Contabilidad** | Registrar, conciliar, cerrar | Facturas con pestaña fiscal, compras B11, NC/ND, pagos/retenciones, bandeja DGII, Salud Fiscal empresa | Config global multiempresa, logs sistema, licencias |
| **Auditor** | Verificar cumplimiento sin modificar | Salud Fiscal, diagnósticos, consumo NCF, exports históricos, bitácora, comparador GL vs DGII | Edición rangos, void, export sin workflow (solo lectura) |
| **Gerente** | Decidir con KPIs | Dashboard Ejecutivo, Salud por empresa, alertas críticas, tendencia consumo, estado cierre mes | Campos técnicos NCF, XML e-CF, configuración diarios |
| **Administrador fiscal** | Operar el centro | Todo el Centro de Administración, wizards, alertas, usuarios fiscales | Código, parámetros servidor, licenciamiento plataforma (salvo catálogo) |
| **Implementador** | Instalar y parametrizar | Wizard configuración inicial, migración, checklist go-live, documentación, sandbox | Operación cotidiana ventas (salvo pruebas) |

## 2.2 Experiencia por rol (detalle)

### Vendedor

**Home:** Ventas → Facturas (vista simplificada) o acceso desde CRM.

**Flujo ideal:** Cliente → Cotización → Confirmar → Factura (2 campos visibles: cliente + líneas). Tipo comprobante **pre-resuelto** desde partner. NCF **oculto** en borrador; visible readonly al confirmar.

**Ayudas:** Banner solo si hay bloqueo (RNC faltante en monto alto, tipo incorrecto). Botón “¿Por qué no puedo facturar?” abre panel contextual, no documentación externa.

**Métrica de éxito:** ≤ 5 clics hasta factura publicada B02/B01.

### Cajero

**Home:** POS con indicador fiscal discreto (semáforo en barra superior del POS).

**Flujo ideal:** Venta → pago → ticket con NCF. Si secuencia < 5%, aviso no bloqueante; si 0, bloqueo con mensaje “Contacte administrador fiscal”.

**No ve:** Menú Fiscal Center completo (salvo permiso explícito).

### Contabilidad

**Home:** Fiscal Center → Mi empresa → Bandeja del día (facturas pendientes validación, compras sin NCF proveedor, exclusiones DGII pendientes).

**Flujo ideal:** Trabajo en cola — resolver items que bajan la Salud Fiscal. Pestaña fiscal en factura solo cuando abre el documento.

**Ve:** Workflow 606/607, retenciones en pagos, asistente NC/ND.

### Auditor

**Home:** Fiscal Center → Salud Fiscal → Modo auditoría (todo read-only, watermark “Vista auditoría”).

**Exporta:** Informes PDF de diagnóstico, historial consumo NCF, trail de aprobaciones DGII.

**No puede:** Publicar, void, cambiar rangos, aprobar exports.

### Gerente

**Home:** Dashboard Ejecutivo (multiempresa si aplica).

**Ve:** Semáforo global, ranking empresas por Salud, top 5 alertas, proyección agotamiento secuencias, estado cierre mes actual.

**Acciones:** Asignar responsable a alerta, snooze con motivo, enlace a reunión de cierre.

### Administrador fiscal

**Home:** Centro de Administración Fiscal.

**Poder:** Rangos, colas, wizards, usuarios fiscales, alertas, configuración por empresa.

**Responsabilidad:** Mantener Salud Fiscal ≥ umbral acordado (ej. 90%).

### Implementador

**Home:** Fiscal Center → Implementación → Checklist.

**Flujo:** Wizard 15 min → empresa operativa → prueba primera factura → activar alertas → entregar credenciales roles.

---

# 3. Mapa completo de navegación

## 3.1 Principios de navegación

1. **Un solo icono de aplicación:** “Fiscal Center” en el app switcher de Odoo.
2. **Profundidad máxima 3 niveles** para tareas frecuentes.
3. **Búsqueda global fiscal** (Cmd+K): “secuencia B01”, “diagnóstico enero”, “rango vencido”.
4. **Contexto empresa** siempre visible en barra superior del producto.
5. **Módulos técnicos invisibles** — el usuario no ve `justech_l10n_do_ncf`; ve “NCF”.

## 3.2 Árbol de navegación propuesto

```
Justech Fiscal Center
│
├── 🏠 Inicio
│   ├── Dashboard Ejecutivo          [Gerente, Admin]
│   ├── Mi bandeja fiscal             [Contabilidad]
│   └── Accesos rápidos              [Personalizado por rol]
│
├── 💚 Salud Fiscal
│   ├── Resumen global               [Score + desglose]
│   ├── Por empresa                  [Drill-down multi-co]
│   ├── Historial de score           [Tendencia 12 meses]
│   ├── Plan de mejora               [Acciones recomendadas]
│   └── Comparar vs período anterior
│
├── 🏢 Empresas
│   ├── Lista de empresas fiscales
│   ├── Perfil fiscal por empresa    [RNC, régimen, flags]
│   ├── Cutover / modo operativo     [Adel→Justech, feature flags]
│   └── Licencias y módulos activos  [Catálogo Justech]
│
├── ⚙️ Configuración
│   ├── Asistente configuración inicial
│   ├── Tipos de contribuyente
│   ├── Tipos de comprobante
│   ├── Diarios fiscales
│   ├── Formas de pago DGII
│   ├── Impuestos y reglas RD
│   ├── Umbrales y parámetros       [250k, alertas %]
│   └── Preferencias UX              [Modo simple / fiscal]
│
├── 🔢 NCF (Serie B)
│   ├── Rangos activos
│   ├── Cola de rangos               [Queued → auto-promote]
│   ├── Consumo y trazabilidad
│   ├── Anulaciones (608)
│   ├── Simulador de consumo
│   └── Operaciones masivas          [Solo admin — import autorización DGII]
│
├── 🔍 Diagnóstico
│   ├── Ejecutar diagnóstico completo
│   ├── Diagnósticos programados
│   ├── Resultados e historial
│   └── Comparar diagnóstico vs cierre real
│
├── 📋 Auditoría
│   ├── Bitácora fiscal unificada
│   ├── Consumo NCF por usuario
│   ├── Cambios configuración
│   ├── Exports DGII descargados
│   └── Void / anulaciones
│
├── 📊 Reportes DGII
│   ├── Centro de cierre mensual
│   ├── 606 Compras
│   ├── 607 Ventas
│   ├── 608 Anulados
│   ├── 609 Pagos exterior
│   ├── 623 Retenciones
│   ├── IT-1 (futuro)
│   ├── Bandeja revisión
│   ├── Bandeja aprobación supervisor
│   └── Historial exports
│
├── 🔔 Alertas
│   ├── Activas
│   ├── Configuración reglas
│   ├── Canales (in-app, email, webhook)
│   └── Silenciadas / snooze log
│
├── 💳 Pagos fiscales                  [v1.1+]
│   ├── Retenciones
│   ├── Medios de pago DGII
│   ├── Conciliación fiscal
│   └── Comprobantes retención
│
├── 📡 e-CF (Comprobantes electrónicos) [v2.0+]
│   ├── Certificados y firma
│   ├── Envíos DGII
│   ├── Cola de contingencia
│   ├── Estados (aceptado/rechazado)
│   └── Representación impresa / QR
│
├── 🌐 DGII en línea                    [v2.0+]
│   ├── Consulta RNC
│   ├── Validación NCF externa
│   ├── Log de integraciones
│   └── Estado servicios DGII
│
├── 🔄 Migración                        [Implementador]
│   ├── Asistente desde Adel
│   ├── Backfill histórico
│   ├── Validación pre-cutover
│   └── Rollback guiado
│
├── 📚 Centro de Ayuda
│   ├── Guías por rol
│   ├── Glosario fiscal RD
│   ├── Videos cortos (< 2 min)
│   ├── FAQ contextual
│   └── Soporte Justech
│
├── 📜 Logs y observabilidad            [Admin técnico]
│   ├── Eventos fiscales
│   ├── Errores integración
│   ├── Métricas consumo
│   └── API JAIOS (read-only)
│
└── ⚙️ Ajustes del producto
    ├── Roles y permisos fiscales
    ├── Personalizar dashboard
    └── Integraciones
```

## 3.3 Mejoras sobre listas genéricas

| Mejora | Descripción |
|--------|-------------|
| **Centro de cierre mensual** | Vista única que orquesta 606+607+608+623 — no menús separados |
| **Mi bandeja fiscal** | Cola personalizada contador — no buscar en contabilidad Odoo |
| **Perfil fiscal empresa** | Una pantalla con todo lo de una empresa — no 8 menús |
| **Modo implementación** | Checklist go-live visible hasta completar 100% |
| **NCF invisible en apps externas** | Ventas/POS consumen API del center — no menú NCF duplicado |

---

# 4. Dashboard Ejecutivo

## 4.1 Propósito

El Dashboard Ejecutivo es el **centro de mando** del Fiscal Center. Debe responder en **≤ 10 segundos** las cinco preguntas del gerente y administrador:

1. ¿Todo está bien?
2. ¿Qué requiere atención **ahora**?
3. ¿Qué empresa tiene problemas?
4. ¿Qué secuencia se agotará primero?
5. ¿Qué acciones puedo tomar sin llamar al contador?

No es un tablero de gráficos decorativos. Es un **sistema de decisión**.

## 4.2 Layout (wireframe conceptual)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  JUSTECH FISCAL CENTER          [Empresa: Todas ▼]    Salud: 87% 🟡      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────────────┐  ┌─────────────────────────────────────────┐ │
│  │ SALUD FISCAL GLOBAL  │  │ REQUIERE ATENCIÓN (5)                    │ │
│  │      87 / 100        │  │ 🔴 JUST OFFICE — B01 agotado en 3 días   │ │
│  │  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░  │  │ 🟠 OMNI — 12 facturas sin tipo ingreso   │ │
│  │  ↓ 3 pts vs mes ant. │  │ 🟠 PLUGSAFE — Cierre Ene pendiente aprob.│ │
│  │  [Ver plan mejora]   │  │ 🟡 JUSTECH — 2 duplicados potenciales    │ │
│  └──────────────────────┘  │ 🟡 JUSTECH — Rango B04 vence en 18 días  │ │
│                            └─────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ EMPRESAS — Salud por compañía                                       │ │
│  │  JUSTECH 92% │ Just Office 71% │ PlugSafe 85% │ Omni 78%          │ │
│  │  [click → drill-down empresa]                                       │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌─────────────────────────┐  ┌──────────────────────────────────────┐ │
│  │ SECUENCIAS — Agotamiento│  │ CIERRE DGII — Mes actual (Jul 2026)  │ │
│  │  1. B01 JUST OFFICE 3d  │  │  606 ████░░ 67%  │ 607 ██████░ 82%    │ │
│  │  2. B02 JUSTECH 12d     │  │  608 ✓ │ 623 ██░░░░ 40%              │ │
│  │  3. B04 OMNI 18d        │  │  [Ir a centro de cierre]             │ │
│  │  [Simular consumo]      │  └──────────────────────────────────────┘ │
│  └─────────────────────────┘                                           │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ ACCIONES RÁPIDAS                                                    │ │
│  │  [+ Rango NCF] [Diagnóstico] [Cierre mes] [Alertas] [Ayuda]       │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌──────────────────────────────┐  ┌──────────────────────────────────┐ │
│  │ Consumo NCF — 30 días        │  │ Errores últimas 24h (2)          │ │
│  │  (sparkline por prefijo)     │  │  • Post bloqueado — duplicado    │ │
│  └──────────────────────────────┘  │  • Export 607 — línea excluida   │ │
│                                     └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

## 4.3 Componentes obligatorios

| Componente | Comportamiento |
|------------|----------------|
| **Salud Fiscal global** | Score 0–100 con color semáforo; clic abre desglose |
| **Lista priorizada atención** | Ordenada por severidad × impacto × antigüedad |
| **Ranking empresas** | Barra horizontal clickeable; multiempresa obligatorio |
| **Proyección agotamiento** | Días restantes = f(remaining, consumo_promedio_30d) |
| **Estado cierre mes** | Progress por formato; enlace directo a bandeja |
| **Acciones rápidas** | Contextuales según rol — no menú genérico |
| **Errores recientes** | Últimas 24–72h con enlace al documento/registro |
| **Consumo tendencia** | Sparklines, no gráficos pesados — carga < 2s |

## 4.4 Reglas de priorización de alertas

```
Severidad = max(
  criticidad_regla,
  impacto_financiero,
  proximidad_vencimiento
)

Orden = Severidad DESC, fecha_deteccion ASC
```

**Crítico (rojo):** imposible facturar en < 7 días, duplicado real confirmado, GL vs fiscal desbalanceado.

**Alto (naranja):** cierre mes incompleto después del día 5, > 10 documentos con error validación.

**Medio (amarillo):** rango vence en 30 días, salud < umbral empresa.

## 4.5 Personalización

- Gerente: vista consolidada multiempresa.
- Admin empresa: vista filtrada a una compañía.
- Widgets reordenables (drag) — máximo 8 visibles.
- “Enfocar modo cierre” oculta widgets operativos y maximiza DGII.

---

# 5. Salud Fiscal

## 5.1 Definición

**Salud Fiscal** es el indicador principal del producto: un **score de 0 a 100** que resume el grado de cumplimiento, preparación operativa y riesgo fiscal de una empresa (o del grupo) en un momento dado.

No es un KPI contable. Es un **índice de confianza** para decidir si se puede operar y cerrar sin sorpresas.

## 5.2 Filosofía

- **Transparente:** el usuario ve exactamente qué resta puntos.
- **Accionable:** cada factor tiene botón “Corregir” o “Asignar”.
- **Histórico:** se guarda snapshot diario para tendencias.
- **No punitivo:** bajar de 100 no es “fallo” — es información.

## 5.3 Modelo de cálculo

Score base = **100 puntos**. Se aplican **deducciones ponderadas** por categoría:

| Categoría | Peso máx. deducción | Factores |
|-----------|:-------------------:|----------|
| **Secuencias NCF** | 25 pts | Agotamiento < 7d, rango vencido, sin cola backup, huecos secuencia |
| **Documentos** | 25 pts | Duplicados, tipo incorrecto, campos DGII faltantes, borradores antiguos |
| **Cierre DGII** | 20 pts | Período anterior sin export, exclusiones sin aprobar, 623 desalineado |
| **Configuración** | 15 pts | RNC inválido, diario sin forma pago, impuestos mal mapeados |
| **Integridad** | 15 pts | Diagnóstico último > 30d, GL vs fiscal mismatch, pagos sin trazar |

**Fórmula:**

```
Salud = 100 - Σ (peso_categoria × severidad_normalizada)

severidad_normalizada ∈ [0, 1] por factor
```

### Ejemplos de deducción

| Factor | Condición | Deducción |
|--------|-----------|:---------:|
| Secuencia crítica | B01 < 3 días restantes | −15 |
| Rango vencido activo | Cualquier prefijo operativo | −20 |
| Duplicado v2.0 confirmado | 1 caso | −10 c/u (max 25) |
| Cierre mes N−1 pendiente | Después del día 5 | −12 |
| Diagnóstico no ejecutado | > 30 días | −5 |

## 5.4 Niveles semáforo

| Rango | Color | Significado | Acción UI |
|:-----:|:-----:|-------------|-----------|
| 90–100 | 🟢 Verde | Operación saludable | Mantener |
| 75–89 | 🟡 Amarillo | Atención preventiva | Plan mejora sugerido |
| 60–74 | 🟠 Naranja | Riesgo operativo | Bandeja priorizada |
| < 60 | 🔴 Rojo | Riesgo crítico | Notificación gerente + bloqueos opcionales |

## 5.5 Plan de mejora automático

Cuando Salud < 90, el sistema genera **Plan de Mejora** ordenado:

1. Acciones de **impacto alto / esfuerzo bajo** primero (quick wins).
2. Cada ítem: descripción, responsable sugerido (rol), ETA estimado, enlace directo.
3. Al completar acción, recálculo en tiempo real del score.

**Ejemplo:**

> “Asignar cola de respaldo para B01 Just Office” → Admin fiscal → 5 min → [Configurar ahora]

## 5.6 Salud Fiscal vs diagnóstico

| | Salud Fiscal | Diagnóstico |
|---|--------------|-------------|
| Frecuencia | Continuo (cached, refresh cada hora) | On-demand o programado |
| Propósito | KPI decisión | Lista exhaustiva hallazgos |
| Audiencia | Gerente, admin | Contador, auditor |
| Profundidad | Resumen ponderado | Detalle técnico completo |

El diagnóstico **alimenta** la Salud Fiscal; no la reemplaza.

---

# 6. Centro de Administración Fiscal

## 6.1 Concepto

No es un menú de listas Odoo. Es el ** cockpit operativo** del administrador fiscal: una sola pantalla con **estado, acciones y profundidad bajo demanda**.

Metáfora: **centro de control de aeropuerto** — ves todos los “vuelos” (secuencias), estado de pistas (rangos), incidentes (alertas), y abres detalle solo cuando necesitas.

## 6.2 Layout maestro

```
┌─────────────────────────────────────────────────────────────────────────┐
│  CENTRO DE ADMINISTRACIÓN FISCAL — JUSTECH SRL                          │
│  Salud: 92% │ Modo: Justech nativo │ Último diagnóstico: hace 2 días    │
├──────────────┬──────────────────────────────────────────────────────────┤
│  NAVEGACIÓN  │  PANEL PRINCIPAL (contextual)                            │
│              │                                                          │
│  ▸ Estado    │  [Según sección seleccionada]                            │
│  ▸ Empresas  │                                                          │
│  ▸ Secuencias│                                                          │
│  ▸ Rangos    │                                                          │
│  ▸ Config    │                                                          │
│  ▸ Auditoría │                                                          │
│  ▸ Diagnóst. │                                                          │
│              │                                                          │
│  ACCIONES    │                                                          │
│  [Wizard +]  │                                                          │
└──────────────┴──────────────────────────────────────────────────────────┘
```

## 6.3 Sección: Estado

**Vista resumen operativo en tiempo real.**

| Tarjeta | Contenido |
|---------|-----------|
| Secuencias activas | 8 prefijos con % consumo mini-barra |
| Próximo vencimiento | Fecha + prefijo |
| Consumo hoy | NCF asignados / void |
| Alertas abiertas | Contador con enlace |
| Cierre mes | % completitud workflow |
| Usuarios activos | Quién consumió NCF hoy (audit) |

## 6.4 Sección: Empresas

Tabla enterprise con columnas: Empresa, RNC, Régimen, Salud, Modo (Adel/Justech/Paralelo), Acciones.

**Acciones por fila:** Perfil fiscal, Cutover, Diagnóstico, Suspender emisión (emergencia).

## 6.5 Sección: Secuencias

Vista **timeline + tabla híbrida:**

- Cada prefijo (B01, B02…) muestra: rango activo, cola, días restantes, consumo/día, gráfico mini 30d.
- Código de color: verde > 30d, amarillo 7–30d, rojo < 7d.
- **Simulador:** “Si mantengo ritmo actual, agoto el ___”.

## 6.6 Sección: Rangos

Lista enriquecida (no tree view cruda):

- Filtros: activo / cola / vencido / agotado.
- Acciones inline: activar, encolar, clonar, archivar.
- Detalle lateral: consumo paginado, autorización DGII scan, journals vinculados.

## 6.7 Sección: Configuración

Agrupada en **acordeones**, no formulario interminable:

1. Identidad fiscal (RNC, razón social DGII)
2. Comportamiento emisión (auto-assign, void policy)
3. Alertas y umbrales
4. Integraciones (e-CF, DGII online — cuando aplique)
5. UX (modo simple default por rol)

## 6.8 Sección: Auditoría

Stream unificado estilo “activity feed”:

- Consumo NCF (quién, cuándo, qué número)
- Void con motivo
- Cambios configuración
- Exports DGII
- Logins administrador fiscal

Filtros: fecha, usuario, tipo evento, prefijo.

## 6.9 Sección: Diagnóstico

- Botón prominente **“Ejecutar diagnóstico completo”**
- Historial con diff entre ejecuciones (“3 hallazgos nuevos desde ayer”)
- Programación: semanal / pre-cierre / pre-export

---

# 7. Asistentes (Wizards) guiados

Principio: **ningún proceso crítico > 7 pasos** en UI. Pasos complejos = backend + progress bar.

## 7.1 Catálogo de asistentes

| Asistente | Pasos | Usuario | Resultado |
|-----------|:-----:|---------|-----------|
| **Configuración inicial** | 5 | Implementador | Empresa fiscal operativa ≤ 15 min |
| **Primera factura** | 3 | Admin + Vendedor | B01 o B02 publicada con validación |
| **Alta de rango NCF** | 4 | Admin fiscal | Rango activo o en cola |
| **Cambio de secuencia** | 5 | Admin fiscal | Cutover sin huecos ni duplicados |
| **Promoción cola rangos** | 2 | Admin / auto | Siguiente rango activo |
| **Cierre fiscal mensual** | 6 | Contabilidad | Exports aprobados listos DGII |
| **Generación reporte DGII** | 3 | Contabilidad | XLSX/TXT tras revisión |
| **Diagnóstico guiado** | 2 | Cualquier rol autorizado | Informe PDF + items en bandeja |
| **Migración desde Adel** | 7 | Implementador | Backfill + validación + cutover |
| **Importación autorización DGII** | 3 | Admin | Rangos precargados desde PDF/Excel |
| **Exportación paquete fiscal** | 2 | Auditor | ZIP período (606+607+608+logs) |
| **Anulación NCF (608)** | 4 | Admin fiscal | Void formal con motivo DGII |
| **NC / ND fiscal** | 3 | Contabilidad | Nota vinculada origen + NCF correcto |
| **Onboarding rol** | 2 | Cualquier rol | Tour interactivo contextual |

## 7.2 Detalle: Configuración inicial (5 pasos)

1. **Identidad** — País DO, RNC, validación checksum, régimen.
2. **Diarios** — Marcar ventas/compras fiscales; forma pago default.
3. **Impuestos** — Confirmar ITBIS 18/0; mapping automático.
4. **Primer rango** — Prefijo, autorización DGII, vigencia, journals.
5. **Prueba** — Publicar factura test sandbox; mostrar NCF; checklist ✅.

Barra progreso persistente. Salir y continuar después.

## 7.3 Detalle: Cierre fiscal mensual (6 pasos)

1. **Pre-check** — Salud Fiscal del período; diagnóstico auto si < 85.
2. **Revisión documentos** — Bandeja excepciones (excluidos, sin NCF, campos faltantes).
3. **Conciliación fiscal** — Pagos ↔ retenciones ↔ 623 preview.
4. **Aprobación supervisor** — Firma digital interna (usuario + timestamp).
5. **Generación** — 606, 607, 608, 623 en paquete.
6. **Entrega** — Descarga + registro hash + “Marcar período cerrado”.

## 7.4 Detalle: Cambio de secuencia (5 pasos)

1. Contexto — prefijo actual, remaining, fecha corte deseada.
2. Nuevo rango — captura o import DGII.
3. Simulación — “X documentos en tránsito”; validación huecos.
4. Ventana cutover — datetime activación; notificación usuarios.
5. Confirmación — activar nuevo, archivar anterior, encolar si aplica.

## 7.5 Reglas UX de wizards

- Siempre **panel lateral** con ayuda contextual del paso actual.
- Errores **inline**, no popup genérico al final.
- **Resumen final** antes de acciones irreversibles.
- **Deshacer** cuando sea posible (void dentro ventana; rollback migración).

---

# 8. Experiencia de usuario

## 8.1 Principios UX del Fiscal Center

| # | Principio | Implementación |
|---|-----------|----------------|
| 1 | **Progressive disclosure** | Mostrar lo mínimo; revelar fiscal bajo demanda |
| 2 | **Fail early, fail clear** | Validar en onchange, no al post |
| 3 | **One home** | Fiscal Center = app; no dispersar en Contabilidad |
| 4 | **Speak human** | Español RD claro; cero códigos sin glosario |
| 5 | **Undo fear** | Histórico sagrado; acciones destructivas con confirmación rica |
| 6 | **Mobile-aware** | Dashboard y alertas legibles en tablet |
| 7 | **Keyboard first** | Power users: atajos en bandeja y búsqueda |
| 8 | **Consistent enterprise** | Misma densidad visual, iconografía, tono en todo el producto |

## 8.2 Modos de experiencia

### Modo Operativo (default ventas/POS)

- Formulario factura: cliente, líneas, total.
- Tipo comprobante: chip sugerido auto (editable solo con permiso).
- NCF: invisible borrador; badge readonly post.
- Alertas: solo bloqueantes.

### Modo Fiscal (default contabilidad)

- Pestaña **Comprobante fiscal** completa.
- Campos income/expense type visibles.
- Enlaces a consumo, void, trazabilidad NC/ND.
- Preview próximo NCF (readonly).

### Modo Administrador

- Acceso completo Fiscal Center.
- Toggle “Ver como rol X” para validar UX.

## 8.3 Reducción de clics — objetivos

| Flujo | Clics hoy (Adel/Justech) | Objetivo Fiscal Center |
|-------|:------------------------:|:----------------------:|
| Factura B02 consumidor | 8–10 | **≤ 5** |
| Compra B11 con NCF proveedor | 6–8 | **≤ 4** |
| Ver estado secuencias | 5+ navegación | **1** (dashboard) |
| Cierre mes DGII | 12+ disperso | **≤ 8** guiados |
| Diagnosticar empresa | No existe / manual | **2** |

## 8.4 Automatización e inteligencia

- **Auto-resolución tipo comprobante** desde partner + journal + monto.
- **Auto-sugerencia cola rangos** cuando remaining < umbral.
- **Auto-exclusión** documentos draft antiguos del cierre (con revisión).
- **Auto-asignación responsable** alerta según rol y empresa.
- **Aprendizaje consumo** — predicción agotamiento (v1.1).

## 8.5 Validaciones inline

Mensajes estructurados:

```
🔴 No se puede publicar
   Motivo: Factura ≥ RD$250,000 requiere RNC del cliente.
   Acción: [Editar cliente] [Cambiar a B01 si aplica]
   Referencia: Norma DGII — Centro de Ayuda §4.2
```

## 8.6 Ayuda contextual

- Tooltips ≤ 120 caracteres.
- Panel “¿Por qué?” expandible.
- Enlace a Centro de Ayuda **anclado al contexto** (no homepage genérica).

---

# 9. Funcionalidades innovadoras

Funcionalidades que posicionan al Fiscal Center **por encima de cualquier competidor** — Adel, Hellenia, localizaciones Odoo community, suites cerradas.

## 9.1 Núcleo innovación (v1.0)

| # | Funcionalidad | Descripción | Diferenciador |
|---|---------------|-------------|---------------|
| 1 | **Salud Fiscal** | Score 0–100 multi-factor | Ningún competidor lo tiene como KPI producto |
| 2 | **Centro de Diagnóstico** | Escaneo read-only automatizado | Adel: manual; Odoo: inexistente |
| 3 | **Dashboard multiempresa** | Consolidado + drill-down | Crítico para grupos como Justgroup |
| 4 | **Plan de mejora automático** | Acciones priorizadas desde Salud | Consultoría embebida |
| 5 | **Bitácora fiscal unificada** | Un stream para todo evento fiscal | Auditoría sin SQL |
| 6 | **Workflow DGII enterprise** | Revisión → aprobación → export | Adel export directo |
| 7 | **Simulador agotamiento secuencias** | Proyección días restantes | Operaciones proactivas |
| 8 | **Centro de cierre mensual** | Orquestador 606+607+608+623 | UX única |
| 9 | **Modo dual Operativo/Fiscal** | Misma data, distinta piel | Cierra brecha UX Adel |
| 10 | **Migración guiada Adel** | Backfill sin repostear | Reduce miedo cambio |

## 9.2 Innovación avanzada (v1.1 – v2.0)

| # | Funcionalidad | Descripción |
|---|---------------|-------------|
| 11 | **IA detección riesgos (JAIOS)** | Modelo lee diagnóstico + histórico; sugiere anomalías (“patrón duplicado proveedor X”) |
| 12 | **Alertas inteligentes** | ML sobre consumo; alerta solo si desviación > σ vs baseline |
| 13 | **Predicción consumo NCF** | Forecast 30/60/90 días por prefijo y empresa |
| 14 | **Recomendaciones automáticas** | “Solicite autorización B01 ahora — agotará antes de aprobación DGII típica” |
| 15 | **Auditorías programadas** | Cron diagnóstico; informe PDF a auditor externo |
| 16 | **Comparador GL vs DGII** | Detecta documentos contabilizados no exportables y viceversa |
| 17 | **What-if NC/ND** | Simula impacto nota crédito en cierre antes de emitir |
| 18 | **Score de proveedores fiscales** | Salud por partner (NCF inválidos, duplicados, retenciones) |
| 19 | **Contingencia e-CF inteligente** | Cola offline; sync automático; Salud incluye estado DGII WS |
| 20 | **Fiscal Copilot (chat)** | Preguntas naturales: “¿Cuántos B01 me quedan?” — respuesta accionable |

## 9.3 Innovación visión v3.0

| # | Funcionalidad | Descripción |
|---|---------------|-------------|
| 21 | **Benchmark anónimo sector** | “Su consumo B02 vs empresas similares” (opt-in) |
| 22 | **Certificación go-live automática** | Checklist + evidencia + PDF certificado Justech |
| 23 | **Marketplace plantillas fiscales** | Config por industria (retail, servicios, importadora) |
| 24 | **Observabilidad OpenTelemetry** | Métricas fiscales exportables a Datadog/Grafana |
| 25 | **Multi-país LATAM shell** | Misma UX; adapters país (visión largo plazo) |

---

# 10. Roadmap del producto

El roadmap es **por versión de producto comercial**, no por sprint técnico interno.

## 10.1 Versión 1.0 — “Confianza operativa” (NCF + DGII core)

**Objetivo:** Reemplazar Adel en clientes RD con experiencia superior y migración segura.

**Incluye:**

| Área | Entregables |
|------|-------------|
| **Product shell** | App Fiscal Center, navegación, roles, búsqueda global |
| **Salud Fiscal v1** | Score + desglose + plan mejora |
| **Dashboard Ejecutivo v1** | Multiempresa, alertas, agotamiento, cierre mes |
| **Centro Administración v1** | Estado, secuencias, rangos, auditoría |
| **NCF serie B** | Motor completo (componente interno) |
| **Reglas DGII core** | B14, 250k, B16, duplicados v2.0, índice SQL v2.0 |
| **Reportes DGII** | 606, 607, 608, workflow revisión/aprobación |
| **Wizards** | Config inicial, cierre mes, cambio secuencia, migración Adel |
| **UX dual** | Modo Operativo + Modo Fiscal |
| **Migración** | `adel_compat` + cutover por empresa |

**No incluye:** e-CF, DGII online, 609 completo, IT-1, IA.

**Criterio éxito v1.0:** Cliente piloto opera 90 días sin Adel; Salud Fiscal ≥ 85 promedio; UAT 4 empresas clon.

---

## 10.2 Versión 1.1 — “Pagos y cierre integrado”

**Objetivo:** Cerrar el ciclo fiscal pago → retención → 623 → 606/607.

**Incluye:**

| Área | Entregables |
|------|-------------|
| **Pagos fiscales** | Retenciones ITBIS/ISR, 5% gobierno, comprobantes |
| **623 exclusivo** | En módulo payments; reports consume adapter |
| **Conciliación fiscal** | Trazabilidad pago ↔ factura ↔ retención |
| **Salud Fiscal v2** | Factor pagos/623 integrado |
| **Predicción consumo** | Forecast secuencias |
| **Alertas email/webhook** | Configurables |
| **609 pagos exterior** | Formato completo |
| **Desacople Hellenia** | Cero dependencia cliente en producto estándar |

**Criterio éxito v1.1:** Cierre mes incluye 623 sin Excel externo; retenciones en Salud Fiscal.

---

## 10.3 Versión 2.0 — “Electrónico y conectado” (e-CF + DGII online)

**Objetivo:** Preparar clientes para e-CF obligatorio sin cambiar de producto.

**Incluye:**

| Área | Entregables |
|------|-------------|
| **e-CF módulo** | E31–E34, XML, firma, envío, QR, contingencia |
| **DGII en línea** | Consulta RNC, validación NCF, log integraciones |
| **Salud Fiscal v3** | Estado WS DGII, cola e-CF, certificados |
| **Serie E + B coexistencia** | Mismo Fiscal Center; reglas claras |
| **Fiscal Copilot v1** | Chat read-only sobre Salud y diagnóstico |
| **POS fiscal integrado** | Mixed payments + e-CF/NCF según régimen |
| **TXT oficial DGII** | Todos los formatos |

**Criterio éxito v2.0:** e-CF en producción piloto; certificación Infile o equivalente en roadmap.

---

## 10.4 Versión 3.0 — “Plataforma fiscal inteligente”

**Objetivo:** El Fiscal Center como plataforma vendible, observable y extensible.

**Incluye:**

| Área | Entregables |
|------|-------------|
| **IA riesgos JAIOS** | Detección anomalías, recomendaciones |
| **IT-1 / IR-17** | Declaraciones extendidas |
| **Marketplace plantillas** | Industria, tamaño empresa |
| **API pública fiscal** | Partners integradores |
| **Observabilidad enterprise** | Métricas, SLOs, alertas ops |
| **Benchmark sector** | Opt-in anónimo |
| **Multi-país foundation** | Shell LATAM (país = config) |

**Criterio éxito v3.0:** Producto listo comercialización masiva RD + primer partner externo.

---

## 10.5 Mapa componentes × versión

| Componente | v1.0 | v1.1 | v2.0 | v3.0 |
|------------|:----:|:----:|:----:|:----:|
| Fiscal Center shell | ✅ | ✅ | ✅ | ✅ |
| Salud Fiscal | v1 | v2 | v3 | v3+IA |
| NCF serie B | ✅ | ✅ | ✅ | ✅ |
| Dashboard | v1 | v1.1 | v2 | v3 |
| Reports 606–608 | ✅ | ✅ | ✅ | ✅ |
| Payments/623 | — | ✅ | ✅ | ✅ |
| e-CF | — | — | ✅ | ✅ |
| DGII online | — | — | ✅ | ✅ |
| IA / JAIOS | — | stub | v1 | v2 |
| IT-1 / IR-17 | — | — | parcial | ✅ |

---

# 11. Estándar visual

## 11.1 Personalidad del producto

**Adjetivos:** Confiable · Claro · Calmo · Preciso · Enterprise

**No es:** Colorido tipo startup, cluttered tipo ERP legacy, técnico tipo consola.

**Metáfora visual:** Centro de control moderno — **cockpit financiero** con semáforos y datos densos pero respirables.

## 11.2 Principios visuales

| Principio | Aplicación |
|-----------|------------|
| **Clarity over decoration** | Cada pixel justifica decisión |
| **Hierarchy through spacing** | Odoo 19 density; whitespace generoso en dashboard |
| **Color = meaning** | Verde/amarillo/naranja/rojo solo Salud y alertas — nunca decorativo |
| **Data near action** | Botón acción junto al dato que resuelve |
| **Fiscal blue anchor** | Primario: azul profundo Justech `#1B3A5C`; acento salud `#0D9488` |
| **Typography** | Inter / system-ui; números tabular para montos y scores |
| **Motion restrained** | Transiciones ≤ 200ms; score anima solo al cambiar |

## 11.3 Componentes visuales propios

| Componente | Especificación |
|------------|----------------|
| **Salud Ring** | Anillo 0–100; grosor 8px; color semáforo; número central bold |
| **Alert Card** | Borde izquierdo 4px severity; icono + título + acción primaria |
| **Sequence Bar** | Progress horizontal por prefijo; tooltip días restantes |
| **Fiscal Chip** | Tipo comprobante (B01, B02) — pill pequeño, readonly en modo operativo |
| **Wizard Stepper** | Horizontal; pasos completados check; actual resaltado |
| **Audit Timeline** | Vertical; avatar usuario; timestamp relativo |

## 11.4 Densidad por superficie

| Superficie | Densidad | Notas |
|------------|----------|-------|
| Dashboard Ejecutivo | Media-alta | KPIs + listas; no formularios |
| Centro Administración | Media | Tablas enriquecidas |
| Factura modo operativo | **Baja** | Máximo aire |
| Factura modo fiscal | Media | Pestañas |
| Wizards | Baja | Un concepto por paso |
| Reportes / exports | Alta | Power users contadores |

## 11.5 Accesibilidad y localización

- Contraste WCAG AA mínimo.
- Iconos siempre con label o tooltip.
- Español RD default; estructura i18n para EN (partners).
- Montos: `RD$ 1,234,567.89` — locale `es_DO`.

## 11.6 Sensación Enterprise

Lograr enterprise **no** es más grises — es:

1. **Consistencia** en toda la app Fiscal Center.
2. **Feedback inmediato** — nunca spinner > 1s sin progreso.
3. **Estados vacíos diseñados** — “Aún no hay rangos” con CTA wizard.
4. **Permisos visibles** — usuario ve qué puede hacer; oculto lo prohibido, no deshabilitado misterioso.
5. **Marca Justech sutil** — logo app switcher; footer “Powered by Justech Fiscal Center vX.Y”.

## 11.7 Relación con Odoo backend

- Heredar design system Odoo 19 (OWL, Bootstrap variables) — **no pelear la plataforma**.
- Componentes fiscales custom en namespace SCSS `jfc-*`.
- Dark mode: compatible fase v1.1 (Salud ring ajustado).

---

# 12. Conclusión crítica — Visión ambiciosa

## 12.1 Veredicto honesto

Justech Fiscal Center **puede** convertirse en el mejor sistema fiscal para Odoo República Dominicana — **pero hoy no existe como producto**. Existe un motor NCF prometedor, reportes parciales y documentación excelente. El salto requerido es de **ingeniería** a **producto**.

Sprint 2 aprobado entregó un componente. Este PDD define el producto que debe envolverlo.

## 12.2 Qué le falta para ser el mejor (sin conservadurismo)

### Brecha 1 — Producto vs módulos

Hoy el cliente percibe “módulos Odoo”. Debe percibir **Fiscal Center**: una app, una Salud, un cierre. Hasta que el shell no exista, competimos con Adel con una mano atada.

### Brecha 2 — UX operativa

Adel gana ventas porque es invisible. Hasta que Modo Operativo no sea default real — no diseño en slide —, vendedores resistirán el cambio. **Meta ambiciosa:** más simple que Adel **y** más potente para contadores.

### Brecha 3 — Migración sin trauma

1.504 NCF y 4 empresas no migrarán por arquitectura bonita. Necesitamos **Migración como feature estrella**: wizard, rollback, paralelo, evidencia automática. Esto debe ser demo comercial #1.

### Brecha 4 — Salud Fiscal como categoría

Nadie en RD vende “salud fiscal” como producto. Si lo ejecutamos bien, **definimos categoría** — como CRM definió pipeline. Objetivo: gerentes dominicanos pregunten “¿cuál es tu Salud Fiscal?” antes de cerrar mes.

### Brecha 5 — e-CF no es add-on tardío

DGII avanzará a e-CF total. v2.0 no es “nice to have” — es **supervivencia comercial**. El Fiscal Center debe comunicar desde v1.0: “Estás en B hoy; el mismo producto te lleva a E mañana”.

### Brecha 6 — IA con propósito, no gimmick

JAIOS no debe ser chatbot decorativo. Debe **reducir tiempo de diagnóstico 80%** y detectar riesgos que humanos no ven (patrones duplicado, proveedores tóxicos, consumo anómalo). Ambición: **auditor fiscal virtual** incluido en licencia.

### Brecha 7 — Producto comercial puro

Cada día que reports dependa de Hellenia, el producto no es vendible. v1.0 **no sale** sin desacople total. No negociable.

### Brecha 8 — Observabilidad y SLA

Enterprise significa **saber antes que el cliente** si algo fallará. Predicción secuencias, alertas proactivas, logs centralizados — ops de Justech monitoreando Salud de clientes (con permiso) en portal partner.

## 12.3 North Star (3 años)

> **Justech Fiscal Center es el sistema con el que el CFO dominicano duerme tranquilo el día 5 de cada mes** — porque a las 9:00 AM ya sabe su Salud Fiscal, qué falta, quién lo resuelve, y que el histórico nunca se tocó.

## 12.4 Métricas de producto (cuando exista v1.0)

| Métrica | Objetivo ambicioso |
|---------|-------------------|
| Time-to-first-invoice (nueva empresa) | ≤ 15 min |
| Salud Fiscal promedio clientes activos | ≥ 88 |
| Clics factura B02 | ≤ 5 |
| Migración Adel sin incidencia crítica | ≥ 95% casos |
| NPS implementadores | ≥ 50 |
| Retención anual licencia fiscal | ≥ 92% |

## 12.5 Próximo paso (post-aprobación PDD)

1. Aprobar este PDD como **fuente única de verdad producto**.
2. Derivar **UX wireframes** de Dashboard, Salud Fiscal y Centro Administración.
3. Derivar **arquitectura técnica producto** (mapa módulos bajo shell Fiscal Center).
4. **Congelar** desarrollo de features sueltos NCF hasta existir shell v1.0.
5. Planificar v1.0 como **release comercial**, no como sprint técnico.

---

## Apéndice A — Mapa módulos técnicos bajo el producto (referencia)

| Módulo técnico | Rol dentro del Fiscal Center |
|----------------|------------------------------|
| `justech_l10n_do_base` | Config, tipos, validators, providers |
| `justech_l10n_do_ncf` | Motor serie B (componente) |
| `justech_l10n_do_reports` | DGII exports + workflow |
| `justech_l10n_do_payments` | Retenciones + 623 |
| `justech_l10n_do_ecf` | Comprobantes electrónicos |
| `justech_l10n_do_dgii` | Integraciones online |
| `justech_l10n_do_dashboard` | **Absorbido en shell Fiscal Center v1.0** |
| `justech_fiscal_center` *(nuevo)* | App shell, Salud Fiscal, navegación, roles UX |

## Apéndice B — Documentos relacionados

| Documento | Relación |
|-----------|----------|
| `JUSTECH_FISCAL_GAP_ANALYSIS.md` | Brechas técnicas pre-producto |
| `JUSTECH_FISCAL_MASTER_PLAN.md` | Arquitectura y principios |
| `evidence/ncf-comparison/` | Benchmark Adel |
| `evidence/fiscal-phase3/SPRINT2_REPORT.md` | Estado componente NCF |

---

## Control de cambios

| Versión | Fecha | Cambio |
|---------|-------|--------|
| 1.0.0 | 2026-07-09 | Emisión inicial PDD — post aprobación Sprint 2 |

---

*Documento de diseño únicamente. No autoriza implementación, despliegue ni cambios en entornos operativos.*

*Cuando este PDD sea aprobado, la construcción seguirá esta visión — no la inversa.*
