# Plan de Pruebas Funcionales — Localización Dominicana (NCF Tradicional)

**Cliente:** Hellenia, S.R.L. — República Dominicana  
**Ambiente objetivo:** `hellenia_dev` (laboratorio)  
**Build:** Odoo `19.0+e-20260619` on-premise  
**Stack fiscal Etapa 1:** `l10n_do` + `l10n_do_reports` (sin `l10n_do_edi`)  
**Fecha:** 2026-06-30  
**Versión:** 1.0  
**Estado:** **Ejecución iniciada 2026-06-30 — DETENIDA en TC-000** (backup VPS pendiente)

---

## Declaración de alcance

Este plan define **32 casos de prueba** (TC-000 a TC-031) para validar la localización dominicana en modo **NCF tradicional** (papel/impreso). Ningún resultado está confirmado hasta ejecutar las pruebas en DEV.

| En alcance | Fuera de alcance |
|------------|------------------|
| Instalación `l10n_do`, `l10n_do_reports` | `l10n_do_edi`, eNCF, Infile |
| Empresa RD, plan contable, impuestos ITBIS | Comunicación electrónica DGII |
| Diarios, secuencias NCF, tipos B01–B04, B11, B13 | POS (plan separado Fase 7) |
| Facturas cliente/proveedor, NC, impresión | Módulos OCA/terceros NCF |
| Reportes fiscales `l10n_do_reports` | Go-live PROD |

**Documentos relacionados:** [NCF_IMPLEMENTATION.md](NCF_IMPLEMENTATION.md) · [GAP_ANALYSIS_RD.md](GAP_ANALYSIS_RD.md) · [IMPLEMENTATION_MASTER_PLAN.md](IMPLEMENTATION_MASTER_PLAN.md)

---

## Convenciones

| Campo | Significado |
|-------|-------------|
| **Resultado obtenido** | Valor real tras ejecutar la prueba — inicialmente `PENDIENTE` |
| **Evidencia** | Captura, log, export o referencia SQL — inicialmente `PENDIENTE` |
| **Conclusión** | `PASS` / `FAIL` / `BLOCKED` / `PENDIENTE` — solo tras ejecución |
| **POR VALIDAR** | Comportamiento esperado según documentación o código; no confirmado |

> **Regla:** Nada se marca como funcionando hasta que el caso correspondiente concluya en `PASS` con evidencia adjunta.

---

## Prerrequisitos globales (antes de TC-001)

| # | Requisito | Estado |
|---|-----------|--------|
| 1 | Ambiente DEV operativo (`hellenia_dev`) | POR VALIDAR |
| 2 | Imagen `hellenia-odoo:19-enterprise` desplegada | POR VALIDAR |
| 3 | `web_enterprise` instalado | POR VALIDAR |
| 4 | Usuario administrador con permisos Contabilidad | POR VALIDAR |
| 5 | BD de laboratorio (sin datos fiscales reales DGII) | POR VALIDAR |
| 6 | **No instalar** `l10n_do_edi` en ningún caso | Obligatorio |
| 7 | Rangos NCF de prueba (ficticios o autorización DGII test) | POR VALIDAR |

---

## Matriz de trazabilidad

| Área funcional | Casos de prueba |
|----------------|-----------------|
| Instalación módulos | TC-000, TC-001, TC-002, TC-003, TC-004 |
| Empresa dominicana | TC-005, TC-006 |
| Plan contable | TC-007, TC-008 |
| Configuración fiscal | TC-009 |
| Impuestos ITBIS / retenciones | TC-010, TC-011, TC-012, TC-013 |
| Diarios | TC-014, TC-015, TC-016 |
| Secuencias y tipos NCF | TC-017, TC-018, TC-019, TC-020, TC-021, TC-022 |
| Facturación cliente | TC-023, TC-024, TC-025, TC-026 |
| Facturación proveedor | TC-027, TC-028, TC-029 |
| Impresión | TC-030 |
| Reportes fiscales | TC-031 |

---

## Resumen de ejecución

| Métrica | Valor |
|---------|-------|
| Total casos | 32 |
| Ejecutados | 0 |
| PASS | 0 |
| FAIL | 0 |
| BLOCKED | 0 |
| PENDIENTE | 31 |
| BLOCKED | 1 (TC-000) |

---

## Casos de prueba

---

### TC-000 — Línea base del ambiente DEV y backup

**Objetivo:** Confirmar prerrequisitos técnicos y crear punto de restauración antes de instalar localización RD.

**Prerequisitos:**
- Acceso a instancia Odoo DEV
- Acceso scripts backup en VPS (`/opt/odoo-projects/hellenia/`)

**Pasos:**
1. Ejecutar `scripts/backup-dev.sh` y verificar integridad (postgres + filestore).
2. Anotar ruta y timestamp del backup para rollback.
3. Verificar versión Odoo (`Settings → About` o CLI `-V`).
4. Confirmar base de datos activa = `hellenia_dev`.
5. Listar módulos instalados: `web_enterprise`, `account`.
6. Confirmar que `l10n_do`, `l10n_do_reports` están **disponibles** en Apps pero **no instalados**.
7. Confirmar que `l10n_do_edi` no está instalado (o ausente en imagen).
8. Registrar fecha/hora y usuario ejecutor.

**Resultado esperado:**
- Backup verificado y ruta documentada
- Odoo 19 Enterprise en DEV operativo
- Módulos RD disponibles sin instalar
- Sin localización DO previamente aplicada

**Resultado obtenido:** Backup completo verificado en VPS vía SSH. Ruta: `/opt/odoo-projects/hellenia/backups/dev/2026-06-30_0353`. Línea base previa capturada en `evidence/l10n-do-tests/2026-06-30/TC-000/result.json`.

**Evidencia:** `backups/dev/2026-06-30_0353/` (postgres_all.sql.gz 615957 B, filestore.tar.gz 635436 B, MANIFEST.txt) + verify-backup-dev.sh OK

**Conclusión:** `PASS` — punto de restauración confirmado. **Esperando aprobación para TC-001.**

**Objetivo:** Instalar el paquete base de localización dominicana y verificar estado del módulo.

**Prerequisitos:**
- TC-000 PASS (o ambiente equivalente validado)
- Permisos para instalar módulos

**Pasos:**
1. Ir a **Apps** → buscar `Dominican Republic` / `l10n_do`.
2. Instalar módulo **Dominican Republic - Accounting** (`l10n_do`).
3. Esperar finalización sin errores en log.
4. Verificar en **Apps** estado = *Installed*.
5. Revisar dependencias satisfechas (`account`, `base_iban`).

**Resultado esperado:**
- `l10n_do` instalado correctamente
- Sin errores traceback en log de Odoo
- Menús de configuración fiscal RD visibles (POR VALIDAR)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-002 — Verificación post-instalación `l10n_do` (datos precargados)

**Objetivo:** Validar que la instalación de `l10n_do` precarga impuestos, secuencias NCF y estructura fiscal base.

**Prerequisitos:**
- TC-001 ejecutado (instalación `l10n_do`)

**Pasos:**
1. Ir a **Contabilidad → Configuración → Impuestos**.
2. Filtrar/buscar impuestos ITBIS (18%, 16%, 0%, exento).
3. Ir a **Contabilidad → Configuración → Diarios** — revisar diarios precargados.
4. Buscar secuencias o tipos de documento NCF (B01, B02, B03, B04, B11, B13, etc.).
5. Revisar **Contabilidad → Declaraciones** / tax report ITBIS si visible.

**Resultado esperado:**
- Impuestos ITBIS precargados según manifest `l10n_do` (POR VALIDAR)
- Secuencias NCF declaradas en manifest presentes en UI (POR VALIDAR)
- Tax report ITBIS con estructura DGII (POR VALIDAR)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-003 — Instalación del módulo `l10n_do_reports`

**Objetivo:** Instalar reportes fiscales dominicanos Enterprise y verificar dependencias.

**Prerequisitos:**
- TC-001 PASS
- `account_reports` instalado (suite contable EE)

**Pasos:**
1. Verificar que `account_accountant` y/o `account_reports` están instalados.
2. Ir a **Apps** → buscar `l10n_do_reports`.
3. Instalar **Dominican Republic - Accounting Reports**.
4. Confirmar instalación sin errores.
5. Verificar auto-instalación o dependencia con `l10n_do` + `account_reports`.

**Resultado esperado:**
- `l10n_do_reports` instalado
- Menú de reportes fiscales RD accesible (POR VALIDAR)
- Sin conflicto con módulos existentes

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-004 — Confirmación de exclusión `l10n_do_edi`

**Objetivo:** Verificar que el módulo de facturación electrónica **no** está instalado ni requerido para NCF tradicional.

**Prerequisitos:**
- TC-001, TC-003 en curso o completados

**Pasos:**
1. Buscar `l10n_do_edi` en Apps.
2. Confirmar estado = *Not Installed* (o módulo ausente en imagen).
3. Intentar emitir factura de prueba **sin** configurar Infile.
4. Documentar si algún flujo exige eNCF para NCF tradicional.

**Resultado esperado:**
- `l10n_do_edi` no instalado
- Flujos NCF tradicional operables sin Infile (POR VALIDAR)
- Sin menú de facturación electrónica RD activo

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-005 — Configuración de empresa — país, moneda y regional

**Objetivo:** Configurar Hellenia como empresa dominicana con parámetros regionales correctos.

**Prerequisitos:**
- TC-001 PASS
- Datos legales Hellenia disponibles (razón social, dirección)

**Pasos:**
1. Ir a **Ajustes → Empresas → [Hellenia]**.
2. Establecer **País** = República Dominicana.
3. Establecer **Moneda** = DOP (RD$).
4. Configurar **Zona horaria** = `America/Santo_Domingo`.
5. Establecer **Idioma** = Español.
6. Guardar y verificar que no se dispare re-instalación conflictiva de localización.

**Resultado esperado:**
- Empresa con país DO, moneda DOP, timezone Santo Domingo
- Localización fiscal RD activa para la compañía (POR VALIDAR)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-006 — Configuración fiscal empresa — RNC y dirección

**Objetivo:** Completar identidad fiscal de la empresa emisora de NCF.

**Prerequisitos:**
- TC-005 PASS
- RNC Hellenia disponible (ej. 133621282 — usar dato oficial acordado)

**Pasos:**
1. En ficha empresa, completar **RNC** / VAT.
2. Completar dirección fiscal: calle, ciudad, provincia, código postal, país DO.
3. Completar teléfono y correo fiscal si aplica.
4. Verificar campos adicionales RD (actividad económica, etc.) si existen en UI.
5. Guardar y revisar que RNC aparece en vista previa de factura.

**Resultado esperado:**
- RNC registrado en empresa
- Dirección fiscal completa
- Datos visibles en documentos impresos (POR VALIDAR)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-007 — Carga y verificación del plan contable dominicano

**Objetivo:** Activar y validar el plan de cuentas DGII/NIIF precargado por `l10n_do`.

**Prerequisitos:**
- TC-001, TC-005 PASS

**Pasos:**
1. Ir a **Contabilidad → Configuración → Ajustes** → sección plan contable.
2. Seleccionar/cargar plantilla **República Dominicana** si no auto-cargada.
3. Abrir **Plan de cuentas** y verificar estructura jerárquica.
4. Confirmar cuentas de activo, pasivo, patrimonio, ingresos, gastos.
5. Exportar listado de cuentas para revisión contador (opcional).

**Resultado esperado:**
- Plan contable DO cargado
- Cuentas alineadas con normativa DGII/NIIF (POR VALIDAR)
- Sin cuentas duplicadas o plantilla incorrecta

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-008 — Verificación de cuentas clave fiscales

**Objetivo:** Confirmar existencia y codificación de cuentas críticas para ITBIS, CxC y CxP.

**Prerequisitos:**
- TC-007 PASS

**Pasos:**
1. Buscar cuenta(s) **ITBIS por pagar / cobrado** en plan contable.
2. Buscar cuenta **Cuentas por cobrar** clientes.
3. Buscar cuenta **Cuentas por pagar** proveedores.
4. Verificar cuentas de **retenciones** si precargadas.
5. Documentar códigos de cuenta encontrados vs. expectativa contador Hellenia.

**Resultado esperado:**
- Cuentas ITBIS venta/compra identificables (POR VALIDAR)
- CxC y CxP configuradas como cuentas por defecto en diarios (POR VALIDAR)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-009 — Configuración del paquete fiscal dominicano

**Objetivo:** Validar que la configuración fiscal de la localización RD está activa y coherente.

**Prerequisitos:**
- TC-001, TC-005, TC-007 PASS

**Pasos:**
1. Ir a **Contabilidad → Configuración → Ajustes** → localización fiscal.
2. Confirmar país fiscal = DO.
3. Revisar opciones específicas RD (redondeo, política precios ITBIS, etc.).
4. Verificar posiciones fiscales precargadas en **Contabilidad → Configuración → Posiciones fiscales**.
5. Documentar opciones disponibles vs. documentación Odoo saas-19.3 (referencia).

**Resultado esperado:**
- Paquete fiscal DO activo
- Posiciones fiscales precargadas visibles (POR VALIDAR)
- Opciones de configuración RD accesibles (POR VALIDAR)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-010 — Impuestos ITBIS ventas (18%, 16%, 0%, exento)

**Objetivo:** Validar impuestos de venta ITBIS precargados y aplicables en líneas de factura.

**Prerequisitos:**
- TC-002, TC-009 PASS
- Producto de prueba creado

**Pasos:**
1. Listar impuestos de venta ITBIS en configuración.
2. Crear factura borrador cliente con producto gravado 18%.
3. Verificar cálculo ITBIS 18% en línea y totales.
4. Repetir con tasa 16% y 0% si disponibles.
5. Probar producto exento si aplica.

**Resultado esperado:**
- Tasas 18%, 16%, 0% y exento configuradas (POR VALIDAR)
- Cálculo automático correcto en factura borrador (POR VALIDAR)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-011 — Impuestos ITBIS compras y crédito fiscal

**Objetivo:** Validar impuestos de compra ITBIS y su contabilización como crédito fiscal.

**Prerequisitos:**
- TC-010 PASS
- Proveedor de prueba creado

**Pasos:**
1. Listar impuestos compra ITBIS (18%, 16%).
2. Crear factura proveedor borrador con ITBIS 18%.
3. Verificar monto ITBIS en líneas y totales.
4. Confirmar factura y revisar asiento contable.
5. Verificar que ITBIS compra va a cuenta crédito fiscal (POR VALIDAR).

**Resultado esperado:**
- ITBIS compra aplicado correctamente
- Asiento contable con crédito fiscal en cuenta esperada (POR VALIDAR)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-012 — Retenciones ITBIS e ISR en compras

**Objetivo:** Validar retenciones fiscales precargadas en operaciones de compra/servicios.

**Prerequisitos:**
- TC-011 PASS
- Proveedor de servicios de prueba con RNC

**Pasos:**
1. Identificar impuestos de retención ITBIS e ISR en configuración.
2. Crear factura proveedor de servicios con retención aplicable.
3. Aplicar posición fiscal o impuesto retención según UI.
4. Confirmar factura y revisar asiento (CxP neto, retención por pagar).
5. Verificar casillas retenciones en tax report ITBIS (POR VALIDAR).

**Resultado esperado:**
- Retenciones configuradas y aplicables (POR VALIDAR)
- Asiento contable refleja monto retenido (POR VALIDAR)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-013 — Posiciones fiscales y exenciones

**Objetivo:** Validar posiciones fiscales precargadas (exenciones ventas al Estado, retenciones exterior, etc.).

**Prerequisitos:**
- TC-009 PASS

**Pasos:**
1. Listar posiciones fiscales RD precargadas.
2. Asignar posición fiscal exención a cliente de prueba gubernamental.
3. Crear factura borrador y verificar cambio de impuestos.
4. Probar posición con retención en compra internacional si existe.
5. Documentar mapeo impuesto por posición fiscal.

**Resultado esperado:**
- Posiciones fiscales operativas (POR VALIDAR)
- Cambio automático de impuestos al seleccionar posición (POR VALIDAR)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-014 — Diarios de ventas con documentos fiscales

**Objetivo:** Configurar diario de ventas con **Use Documents** habilitado para emisión NCF.

**Prerequisitos:**
- TC-002, TC-017 (tipos NCF identificados)

**Pasos:**
1. Ir a **Contabilidad → Configuración → Diarios**.
2. Crear o editar diario **Ventas Fiscal**.
3. Tipo = Ventas; habilitar **Use Documents** / documentos LATAM (POR VALIDAR etiqueta UI 19.0).
4. Vincular tipos documento B01 y B02 al diario.
5. Configurar secuencia y cuentas por defecto.
6. Guardar y verificar diario listo para facturación fiscal.

**Resultado esperado:**
- Diario ventas con documentos fiscales habilitado
- Tipos B01/B02 seleccionables al facturar (POR VALIDAR)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-015 — Diarios de compras con documentos fiscales

**Objetivo:** Configurar diario de compras para registro de NCF de proveedores y tipos B11/B13.

**Prerequisitos:**
- TC-014 PASS

**Pasos:**
1. Crear/editar diario **Compras Fiscal**.
2. Tipo = Compras; habilitar documentos si aplica en 19.0.
3. Vincular tipos documento compra según UI disponible.
4. Configurar cuentas gasto/inventario, ITBIS, CxP.
5. Verificar compatibilidad con flujo unificado de diarios compra (PR #62330 — POR VALIDAR en 19.0).

**Resultado esperado:**
- Diario compras operativo para facturas proveedor
- Soporte registro NCF entrada (POR VALIDAR)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-016 — Diarios financieros (banco y efectivo)

**Objetivo:** Validar diarios banco/efectivo sin NCF para pagos y conciliación.

**Prerequisitos:**
- TC-007 PASS

**Pasos:**
1. Revisar diarios **Banco** y **Efectivo/Caja** precargados o crearlos.
2. Configurar cuentas conte de banco y efectivo.
3. Registrar pago de cliente contra factura de prueba.
4. Verificar asiento de pago sin asignación NCF.
5. Confirmar separación flujo fiscal vs. financiero.

**Resultado esperado:**
- Diarios financieros operativos
- Pagos no generan NCF (comportamiento esperado)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-017 — Catálogo de tipos de documento NCF

**Objetivo:** Inventariar tipos NCF disponibles tras instalar `l10n_do` y mapearlos a códigos DGII.

**Prerequisitos:**
- TC-001, TC-002 PASS

**Pasos:**
1. Ir a **Contabilidad → Configuración → Tipos de documento** (o equivalente 19.0).
2. Listar todos los tipos: B01, B02, B03, B04, B11, B12, B13, B14, B15, B16.
3. Documentar cuáles existen vs. cuáles faltan.
4. Comparar con secuencias declaradas en manifest `l10n_do`.
5. Registrar gaps en [GAP_ANALYSIS_RD.md](GAP_ANALYSIS_RD.md) si aplica.

**Resultado esperado:**
- Tipos prioritarios B01, B02, B03, B04 presentes (POR VALIDAR)
- Tipos secundarios B11, B13 presentes (POR VALIDAR)
- B14, B15, B16 — existencia POR VALIDAR

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-018 — Configuración de rango NCF B01 (Crédito Fiscal)

**Objetivo:** Registrar rango autorizado DGII para comprobantes B01 y vincularlo al diario ventas.

**Prerequisitos:**
- TC-014, TC-017 PASS
- Rango B01 de prueba (inicio, fin, vencimiento)

**Pasos:**
1. Ir a configuración de rangos/secuencias NCF por tipo documento.
2. Crear rango B01: prefijo B01, secuencial inicio/fin, fecha vencimiento.
3. Vincular rango al diario ventas B01.
4. Verificar formato `B01XXXXXXXXXX` (11 dígitos secuenciales).
5. Confirmar rango activo y próximo número disponible.

**Resultado esperado:**
- Rango B01 configurado sin errores (POR VALIDAR)
- Sistema muestra próximo NCF disponible (POR VALIDAR)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-019 — Configuración de rango NCF B02 (Consumo)

**Objetivo:** Registrar rango autorizado DGII para comprobantes B02 (consumidor final).

**Prerequisitos:**
- TC-014, TC-017 PASS
- Rango B02 de prueba

**Pasos:**
1. Crear rango B02 con secuencia inicio/fin y vencimiento.
2. Vincular al diario ventas B02 o mismo diario con selección tipo.
3. Verificar formato `B02XXXXXXXXXX`.
4. Confirmar independencia de rangos B01 vs B02.
5. Documentar configuración para uso POS futuro.

**Resultado esperado:**
- Rango B02 configurado (POR VALIDAR)
- Rangos B01 y B02 no comparten secuencia (POR VALIDAR)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-020 — Asignación automática de NCF al confirmar factura

**Objetivo:** Verificar que el sistema consume secuencia NCF al publicar/confirmar factura de venta.

**Prerequisitos:**
- TC-018 o TC-019 PASS (rango activo)
- Cliente y producto de prueba

**Pasos:**
1. Crear factura borrador B02 (consumidor final).
2. Verificar que NCF **no** está asignado en borrador (POR VALIDAR).
3. Confirmar/publicar factura.
4. Verificar NCF asignado con formato correcto.
5. Crear segunda factura y confirmar incremento secuencial.
6. Revisar advertencia manifest legacy sobre secuencias sin terceros.

**Resultado esperado:**
- NCF asignado al confirmar (POR VALIDAR — crítico)
- Secuencia incrementa correctamente (POR VALIDAR)
- Sin requerir módulos terceros (POR VALIDAR — validar advertencia manifest)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-021 — Vencimiento y agotamiento de rango NCF

**Objetivo:** Validar comportamiento del sistema ante rango NCF vencido o agotado.

**Prerequisitos:**
- TC-020 PASS
- Rango de prueba con límite bajo (ej. 2 números) o fecha vencida simulada

**Pasos:**
1. Configurar rango con 1–2 números restantes o fecha vencimiento pasada.
2. Emitir facturas hasta agotar rango.
3. Intentar emitir factura adicional.
4. Documentar mensaje de error o bloqueo.
5. Renovar rango y verificar emisión reanuda.

**Resultado esperado:**
- Sistema bloquea emisión sin NCF disponible (POR VALIDAR)
- Mensaje claro al usuario (POR VALIDAR)
- Nuevo rango permite continuar (POR VALIDAR)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-022 — Tipos NCF B03 (Nota Débito) y B04 (Nota Crédito)

**Objetivo:** Validar disponibilidad y configuración de rangos para notas débito y crédito.

**Prerequisitos:**
- TC-017 PASS

**Pasos:**
1. Verificar tipos documento B03 y B04 en catálogo.
2. Configurar rangos B03 y B04 de prueba.
3. Vincular a diarios correspondientes.
4. Documentar si requieren diario separado o mismo diario ventas.
5. Registrar gaps si tipos no configurables.

**Resultado esperado:**
- B03 y B04 configurables con rangos (POR VALIDAR)
- Diarios soportan NC/ND (POR VALIDAR)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-023 — Factura cliente B01 — Crédito Fiscal (B2B)

**Objetivo:** Emitir factura de crédito fiscal a cliente con RNC (tipo B01).

**Prerequisitos:**
- TC-018, TC-020 PASS
- Cliente B2B con RNC válido de prueba
- Producto gravado ITBIS 18%

**Pasos:**
1. Crear cliente con RNC en campo VAT/RNC.
2. Crear factura en diario ventas fiscal.
3. Seleccionar tipo documento B01 (automático o manual — POR VALIDAR).
4. Agregar líneas con ITBIS 18%.
5. Confirmar factura.
6. Verificar NCF B01, asiento contable (Ingreso + ITBIS cobrado + CxC).

**Resultado esperado:**
- Factura B01 con NCF asignado (POR VALIDAR)
- ITBIS 18% calculado correctamente (POR VALIDAR)
- Asiento contable cuadrado (POR VALIDAR)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-024 — Factura cliente B02 — Consumidor Final (B2C)

**Objetivo:** Emitir factura consumo final sin RNC (tipo B02).

**Prerequisitos:**
- TC-019, TC-020 PASS
- Cliente genérico consumidor final

**Pasos:**
1. Crear factura para cliente sin RNC (consumidor final).
2. Seleccionar tipo documento B02.
3. Agregar productos con ITBIS según política precios.
4. Confirmar factura.
5. Verificar NCF B02 y totales.
6. Validar selección automática B01 vs B02 según RNC cliente (POR VALIDAR).

**Resultado esperado:**
- Factura B02 emitida con NCF (POR VALIDAR)
- Tipo documento coherente con perfil cliente (POR VALIDAR)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-025 — Nota de crédito B04 con referencia NCF origen

**Objetivo:** Crear nota de crédito vinculada a factura original con NCF de referencia.

**Prerequisitos:**
- TC-023 o TC-024 PASS (factura origen confirmada)
- TC-022 PASS (rango B04)

**Pasos:**
1. Abrir factura origen confirmada (B01 o B02).
2. Crear **Nota de crédito** desde factura (botón estándar Odoo).
3. Seleccionar tipo documento B04.
4. Verificar referencia al NCF origen.
5. Confirmar NC parcial o total.
6. Revisar asiento reversión ingreso e ITBIS; NCF B04 asignado.

**Resultado esperado:**
- NC B04 con NCF propio y referencia origen (POR VALIDAR)
- Reversión contable correcta (POR VALIDAR)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-026 — Nota de débito B03

**Objetivo:** Crear nota de débito que incrementa monto de factura original.

**Prerequisitos:**
- TC-023 PASS
- TC-022 PASS (rango B03)

**Pasos:**
1. Desde factura B01 confirmada, crear nota de débito.
2. Seleccionar tipo B03.
3. Agregar línea de ajuste positivo con ITBIS.
4. Confirmar ND.
5. Verificar NCF B03 y asiento contable incremental.

**Resultado esperado:**
- ND B03 emitida con NCF (POR VALIDAR)
- Incremento CxC e ITBIS correcto (POR VALIDAR)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-027 — Factura proveedor con ITBIS crédito fiscal

**Objetivo:** Registrar factura de compra con NCF proveedor e ITBIS acreditable.

**Prerequisitos:**
- TC-015, TC-011 PASS
- Proveedor con RNC de prueba

**Pasos:**
1. Crear factura proveedor en diario compras.
2. Ingresar NCF del proveedor (campo disponible — POR VALIDAR).
3. Agregar líneas con ITBIS 18% compra.
4. Confirmar factura.
5. Verificar asiento: Gasto/Inventario + ITBIS pagado (crédito) + CxP.

**Resultado esperado:**
- Factura proveedor registrada con ITBIS crédito (POR VALIDAR)
- NCF proveedor registrado en documento (POR VALIDAR)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-028 — Factura proveedor con retenciones ISR/ITBIS

**Objetivo:** Validar compra con retenciones aplicadas y neto a pagar correcto.

**Prerequisitos:**
- TC-012, TC-027 PASS

**Pasos:**
1. Crear factura proveedor de servicios profesionales.
2. Aplicar retención ISR y/o ITBIS según configuración.
3. Confirmar factura.
4. Verificar asiento: CxP neto, retenciones por pagar, ITBIS crédito.
5. Validar impacto en tax report retenciones (POR VALIDAR).

**Resultado esperado:**
- Retenciones descontadas del neto a pagar (POR VALIDAR)
- Cuentas retención correctas (POR VALIDAR)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-029 — Comprobante proveedor informal B11

**Objetivo:** Registrar compra a proveedor informal usando tipo documento B11.

**Prerequisitos:**
- TC-017, TC-015 PASS
- Proveedor sin RNC formal de prueba

**Pasos:**
1. Crear proveedor informal (sin RNC o categoría informal).
2. Crear factura/documento en diario compras tipo B11.
3. Configurar rango B11 si requerido.
4. Confirmar documento.
5. Verificar NCF B11 y asiento contable.

**Resultado esperado:**
- Flujo B11 operativo (POR VALIDAR)
- NCF B11 asignado o registrado (POR VALIDAR)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-030 — Impresión PDF factura con datos fiscales NCF

**Objetivo:** Validar que el PDF de factura cliente incluye datos fiscales mínimos para NCF tradicional.

**Prerequisitos:**
- TC-023 o TC-024 PASS (factura confirmada con NCF)

**Pasos:**
1. Abrir factura confirmada con NCF (B01 o B02).
2. Imprimir / generar PDF.
3. Verificar presencia de: RNC emisor, RNC receptor (si B01), NCF completo, fecha, ITBIS desglosado, totales, dirección empresa.
4. Validar legibilidad y cumplimiento mínimo formato DGII en documento impreso (revisión contador).

**Resultado esperado:**
- PDF generado sin error (POR VALIDAR)
- NCF, RNC e ITBIS visibles en documento (POR VALIDAR)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

### TC-031 — Reportes fiscales `l10n_do_reports`

**Objetivo:** Validar disponibilidad y operación de reportes fiscales dominicanos tras instalar `l10n_do_reports`.

**Prerequisitos:**
- TC-003 PASS
- TC-023/024 y TC-027 PASS (movimientos de prueba en período)

**Pasos:**
1. Ir a **Contabilidad → Informes** (o menú reportes EE).
2. Listar todos los reportes `l10n_do_reports` disponibles (sin asumir nombres).
3. Ejecutar reporte ventas / libro 607 (si existe) — período con facturas TC-023/024.
4. Ejecutar reporte compras / libro 606 (si existe) — período con TC-027.
5. Ejecutar reporte anulaciones / 608 (si existe) — tras anular documento de prueba.
6. Ejecutar declaración ITBIS / tax report / IT-1 (si existe).
7. Verificar que operaciones de prueba aparecen con NCF e ITBIS correctos.
8. Exportar a Excel/PDF si disponible.

**Resultado esperado:**
- Reportes fiscales RD accesibles post `l10n_do_reports` (POR VALIDAR)
- Libros 606/607/608/IT-1 operativos o brecha documentada en GAP_ANALYSIS (POR VALIDAR)
- Exportación funcional (POR VALIDAR)

**Resultado obtenido:** PENDIENTE

**Evidencia:** PENDIENTE

**Conclusión:** PENDIENTE

---

## Orden de ejecución recomendado

```
TC-000 → TC-001 → TC-002 → TC-003 → TC-004
    → TC-005 → TC-006 → TC-007 → TC-008 → TC-009
    → TC-010 → TC-011 → TC-012 → TC-013
    → TC-017 → TC-014 → TC-015 → TC-016
    → TC-018 → TC-019 → TC-020 → TC-021 → TC-022
    → TC-023 → TC-024 → TC-025 → TC-026
    → TC-027 → TC-028 → TC-029 → TC-030 → TC-031
```

---

## Criterios de salida (Etapa 1 NCF tradicional)

| Criterio | Condición |
|----------|-----------|
| Instalación | TC-001, TC-003 PASS; TC-004 confirma sin `l10n_do_edi` |
| Empresa y plan | TC-005 a TC-009 PASS |
| Impuestos | TC-010 a TC-013 PASS |
| NCF operativo | TC-020 PASS (crítico — asignación NCF) |
| Facturación | TC-023, TC-024 PASS mínimo |
| Ajustes | TC-025 PASS |
| Compras | TC-027 PASS mínimo |
| Reportes | TC-031 PASS |
| Impresión | TC-030 PASS |

Si **TC-020 FAIL**, escalar a [GAP_ANALYSIS_RD.md](GAP_ANALYSIS_RD.md) — brecha secuencias NCF manifest legacy.

---

## Registro de ejecución

| Campo | Valor |
|-------|-------|
| Ejecutor | PENDIENTE |
| Fecha inicio | PENDIENTE |
| Fecha fin | PENDIENTE |
| Ambiente | `hellenia_dev` |
| Acta de resultados | PENDIENTE |

---

**Versión:** 1.0  
**Mantenido por:** Consultoría implementación Justech  
**Próximo paso:** Aprobación para ejecutar TC-000 — sin instalación hasta autorización explícita
