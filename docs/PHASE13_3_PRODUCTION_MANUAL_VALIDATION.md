# Fase 13.3 — Validación manual final en PRODUCCIÓN

**Fecha:** 2026-06-30 (UTC)  
**URL:** https://odoo.hellenia.cloud  
**Base de datos:** `hellenia_prod`  
**Validador:** Cloud Agent (validación funcional + revisión UI vía shell/HTTP)  
**Evidencia:** `evidence/phase13-3-validate-prod.json`  
**Prerequisito:** Fase 13.2 PASS (corrección fiscal ITBIS)

---

## Resultado global

# PASS CON OBSERVACIONES

La corrección fiscal y los flujos operativos Justech funcionan correctamente en producción. No se detectó impuesto 15% en ventas nuevas. Quedan observaciones de UX e infraestructura que deben resolverse antes del go-live a usuarios finales de Hellenia.

**Go-Live definitivo:** NO ejecutado (según instrucción).

---

## Checklist de validación (11 puntos)

| # | Verificación | Resultado | Evidencia |
|---|--------------|-----------|-----------|
| 1 | Cotización nueva creada | **PASS** | SO en borrador generada en validación |
| 2 | Producto en cotización | **PASS** | Producto existente con impuesto asignado |
| 3 | Impuesto ITBIS 18%, no 15% | **PASS** | Línea con `[18.0]`; `active_15=0` |
| 4 | App en español | **PASS CON OBS.** | Usuarios `es_DO`; login ES con `Accept-Language: es-DO` |
| 5 | Menús principales | **PASS CON OBS.** | Ver tabla menús abajo |
| 6 | Factura B01 | **PASS** | NCF `B0100009000` — INV/2026/00001 |
| 7 | Factura B02 | **PASS** | NCF `B0200009000` — INV/2026/00002 |
| 8 | Nota de crédito B04 | **PASS** | NCF `B0400009000` |
| 9 | Reportes 606, 607, 608 | **PASS** | 2 / 2 / 1 líneas respectivamente |
| 10 | PDF factura con NCF | **PASS** | 56,966 bytes |
| 11 | Logs sin errores fiscales | **PASS CON OBS.** | Sin errores contables/fiscales; ver logs websocket |

---

## Detalle por bloque

### 1–3. Cotización e impuestos

Validación ejecutada en producción (`phase13-2-validate-fiscal.py`, 2026-06-30 16:06 UTC):

| Métrica | Valor |
|---------|-------|
| Impuesto 15% activo | 0 |
| ITBIS venta | `18% ITBIS` |
| Línea cotización | `[18.0]` — sin 15% |
| Plan contable | 288 cuentas (plan `do`) |

**Antes (Fase 13.2):** impuesto `account.1_sale_tax_template` al 15%, plan `generic_coa`.  
**Ahora:** ITBIS 18% correcto en cotizaciones y facturas nuevas.

### 4. Español

| Ámbito | Estado | Detalle |
|--------|--------|---------|
| Idioma compañía | PASS | `es_DO` |
| Usuarios internos (2) | PASS | Ambos `es_DO` |
| Menús Justech | PASS | "Reportes DGII", "Fiscal dominicano" |
| Login público | OBS | Sin header de idioma: labels EN; con `es-DO`: "Iniciar sesión", "Correo", "Contraseña" |
| Menú Ajustes | OBS | Visible como **"Ajustes"** (traducción Odoo `es_DO`), no "Configuración" |

### 5. Menús principales (usuario admin, `es_DO`)

Menús raíz activos verificados:

| Requerido | Visible en PROD | Estado |
|-----------|-----------------|--------|
| Ventas | Ventas | PASS |
| Compras | Compras | PASS |
| Inventario | Inventario | PASS |
| Contabilidad | Contabilidad | PASS |
| Contactos | Contactos | PASS |
| Configuración | Ajustes | PASS CON OBS. |

**Observación UX:** coexisten **Facturación** y **Contabilidad** en el menú raíz (efecto de `hellenia_ui` + menú estándar Odoo). No bloquea operación pero debe limpiarse antes del go-live visual.

Módulos instalados: `sale_management`, `purchase`, `stock`, `account`, `hellenia_ui`.

### 6–8. Documentos fiscales NCF

| Tipo | NCF | Asiento |
|------|-----|---------|
| B01 (crédito fiscal) | B0100009000 | INV/2026/00001 |
| B02 (consumidor final) | B0200009000 | INV/2026/00002 |
| B04 (nota de crédito) | B0400009000 | Generada en validación |

ITBIS en facturas B01/B02: **18%** (líneas `-900.0` sobre base 5,000).

**Nota:** secuencias en rango de prueba `9000–9999` (P13.2). Reemplazar por rangos DGII autorizados antes de operación real.

### 9. Reportes DGII

| Reporte | Líneas | Total |
|---------|--------|-------|
| 606 — Compras | 2 | 4,720.00 |
| 607 — Ventas | 2 | 6,018.00 |
| 608 — NCF anulados | 1 | — |

Generados desde **Contabilidad → Reportes DGII** con totales, período y trazabilidad (v1.2.0).

### 10. PDF factura

- Plantilla con campo **NCF** y **Tipo de documento** (español)
- Tamaño: 56,966 bytes
- NCF impreso en factura de prueba

### 11. Logs

| Tipo | Resultado |
|------|-----------|
| Errores fiscales / contables / NCF | **Ninguno** en últimos 30 min |
| Errores HTTP websocket (puerto 8072) | **Presentes** (~145 en 10 min) |

```
RuntimeError: Couldn't bind the websocket. Is the connection opened on the evented port (8072)?
```

**Impacto:** notificaciones en tiempo real / bus Odoo pueden fallar; **HTTP, facturación, reportes y PDF operan con normalidad**. Corregir configuración Traefik/longpolling en ventana de mantenimiento.

---

## Infraestructura

| Check | Estado |
|-------|--------|
| HTTPS `/web/login` | 200 OK |
| Contenedor `hellenia-prod-odoo-1` | healthy |
| Contenedor `hellenia-prod-db-1` | healthy |
| `odoo-pecv` | Sin cambios |

---

## Pendientes antes de abrir el sistema a Hellenia

| Prioridad | Pendiente | Acción |
|-----------|-----------|--------|
| **Alta** | Rangos NCF reales DGII (B01–B13) | Cargar secuencias autorizadas; retirar rangos de prueba 9000 |
| **Alta** | Datos maestros Hellenia | Productos, clientes, proveedores, cuentas por categoría |
| **Media** | Menú duplicado Facturación/Contabilidad | Ajuste `hellenia_ui` en PROD |
| **Media** | WebSocket / longpolling (8072) | Configurar Traefik para bus Odoo |
| **Media** | Ocultar menú "Pruebas" en PROD | Restringir a grupo técnico |
| **Baja** | Login sin idioma del navegador | Forzar redirect `es_DO` o traducción login |
| **Baja** | Etiqueta "Ajustes" vs "Configuración" | Alinear traducción menú si se desea nombre exacto |

---

## ¿Producción lista para configurar datos reales?

# SÍ — con las reservas anteriores

| Criterio | Listo |
|----------|-------|
| Impuestos RD (ITBIS 18%) | Sí |
| Plan contable dominicano | Sí |
| Localización Justech (NCF, reportes) | Sí — funcional |
| Módulos operativos (Ventas, Compras, etc.) | Sí |
| Rangos NCF de producción DGII | **No** — usar rangos reales |
| Datos de negocio Hellenia | **No** — pendiente importación |
| Go-live usuarios finales | **No** — resolver pendientes alta/media |

**Recomendación:** proceder con **carga de datos maestros y rangos NCF reales** en producción. Mantener go-live de usuarios hasta cerrar websocket y limpieza de menú.

---

## Referencias

- `docs/PRODUCTION_TAX_AND_REPORTS_FIX.md` — corrección Fase 13.2
- `docs/TAX_FIX_TEST_REPORT.md` — certificación TEST
- `evidence/phase13-3-validate-prod.json` — evidencia funcional PROD (2026-06-30 16:06 UTC)
- Backup pre-corrección: `backups/hellenia-prod/2026-06-30_1558`

---

**Certificación Fase 13.3:** PASS CON OBSERVACIONES — producción fiscalmente correcta; lista para parametrización de datos reales, no para go-live público aún.
