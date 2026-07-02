# Fase 13.4 — Reporte de hardening de producción

**Fecha:** 2026-06-30 (UTC)  
**Entorno:** `hellenia_prod` — https://odoo.hellenia.cloud  
**Backup previo:** `backups/hellenia-prod/2026-06-30_1618`  
**Evidencia:** `evidence/phase13-4-hardening-prod.json`  
**Rama:** `cursor/production-hardening-phase13-4-dd85`

---

## Resumen ejecutivo

| Bloque | Resultado |
|--------|-----------|
| 1. Limpieza piloto/UAT | **PASS** |
| 2. Menú principal | **PASS CON OBS.** |
| 3. Traducciones Justech | **PASS** |
| 4. WebSocket / longpolling | **PASS** |
| 5. Auditoría permisos | **PASS CON OBS.** |
| 6. Localización Justech | **PASS CON OBS.** |
| 7. Efecto contable (smoke) | **PASS** |
| **Hardening global** | **PASS CON OBSERVACIONES** |

---

## 1. Limpieza entorno de pruebas

### Acciones ejecutadas

| Acción | Resultado |
|--------|-----------|
| Eliminar producto "Prueba" | 1 eliminado |
| Eliminar partners UAT/P13 | 0 (no existían) |
| Eliminar reportes fiscales prueba | 0 |
| Eliminar rangos NCF prueba (9000+) | 0 activos |
| Ocultar menú Tests/Pruebas | `base.menu_tests` → inactivo |

### Verificación post-limpieza

| Métrica | Valor |
|---------|-------|
| Partners UAT (`ref` UAT%) | 0 |
| Partners P13 | 0 |
| Productos UAT | 0 |
| Producto "Prueba" | 0 |
| Rangos NCF secuencia ≥9000 | 0 |

### Residuos smoke P13.4 (documentados)

Quedan artefactos de la prueba contable de hardening (no UAT histórico):

| Tipo | Detalle | Acción antes Go-Live |
|------|---------|---------------------|
| Facturas | INV/2026/00001–00003 | Anular/archivar o eliminar según política contador |
| Partners | SMOKE P13.4 CF (×2) | Eliminar tras reversar facturas |
| Productos | SMOKE-P134-DELETE (×2) | Eliminar tras limpiar líneas |
| Rango NCF | SMOKE P13.4 B02 | Expirar tras liberar facturas |

---

## 2. Menú principal

### Menús ocultos

| XML ID | Nombre original |
|--------|-----------------|
| `base.menu_tests` | Tests / Pruebas |
| `mail.menu_root_discuss` | Discuss / Conversaciones |
| `spreadsheet_dashboard.spreadsheet_dashboard_menu_root` | Dashboards / Tableros |
| `utm.menu_link_tracker_root` | Link Tracker |
| `accountant.menu_accounting` | Accounting (duplicado) |

### Menús raíz visibles (admin, `es_DO`)

1. Contactos  
2. Ventas  
3. Contabilidad  
4. Compras  
5. Inventario  
6. Configuración  
7. **Aplicaciones** — solo `group_system` (admin técnico)

**Observación:** "Facturación" y "Accounting" duplicados **eliminados**. "Aplicaciones" permanece visible para administradores con permiso técnico; usuarios operativos Hellenia (cuando se creen) no la verán si no tienen `group_system`.

### Etiquetas en español aplicadas

| Menú | Etiqueta |
|------|----------|
| Ventas | Ventas |
| Compras | Compras |
| Inventario | Inventario |
| Contactos | Contactos |
| Contabilidad | Contabilidad |
| Configuración | Configuración |

---

## 3. Traducciones

| Ámbito | Estado |
|--------|--------|
| Menús Justech (DGII, NCF, Fiscal) | Actualizados a español |
| Textos inglés en módulos Justech | **0** detectados |
| Core Odoo (`l10n_do`, impuestos) | Nombres técnicos en inglés — no modificable |

### Textos estándar Odoo que permanecen en inglés

| Origen | Ejemplo | Motivo |
|--------|---------|--------|
| Nombres impuestos `l10n_do` | "18% ITBIS", "ITBIS Exempt" | Localización oficial Odoo |
| Posiciones fiscales | "DO Domestic", "Restaurants" | Plantilla `l10n_do` |
| Login sin `Accept-Language` | "Log in" | Traducción navegador; con `es-DO` muestra español |
| Algunos tooltips core | Varios | Core/Enterprise — no modificable |

---

## 4. WebSocket / Traefik

### Correcciones aplicadas

1. **`odoo.conf`:** `longpolling_port` → `gevent_port = 8072` (Odoo 19)
2. **Traefik labels** en `docker/production/docker-compose.yml`:
   - Router `hellenia-prod-ws` → `PathPrefix(/websocket)` y `/longpolling` → puerto **8072**
   - Router principal → puerto **8069**

### Validación

| Check | Antes P13.4 | Después P13.4 |
|-------|-------------|---------------|
| Errores `Couldn't bind the websocket` (5 min) | ~145 | **0** |
| Proceso gevent en contenedor | Activo | Activo |
| Endpoint `/websocket` vía HTTPS | Error en bus | HTTP 400 (handshake esperado) |
| `proxy_mode` | True | True |

---

## 5. Auditoría de permisos

| Check | Resultado |
|-------|-----------|
| Record rules Justech (`fiscal.report`, `ncf.range`, `document.type`) | 1 regla c/u |
| Usuarios internos activos | 2 (`admin`, `it@justech.do`) |
| Usuarios sin `group_system` | 0 (pendiente crear usuarios Hellenia) |
| Menú Apps restringido | `group_system` only |

**Observación:** No hay aún usuarios operativos Hellenia para validar vista restringida; se validará al importar usuarios.

---

## 6. Auditoría localización Justech

| Componente | Estado |
|------------|--------|
| `justech_l10n_do_base` | Instalado |
| `justech_l10n_do_ncf` | Instalado |
| `justech_l10n_do_reports` | Instalado |
| `l10n_do` | Instalado |
| Tipos documento B01/B02/B03/B04/B11/B13 | 6 tipos |
| Fiscal habilitado | Sí |
| Rangos NCF activos | **0** (pendiente DGII) |
| Reportes DGII | Funcionales (validado Fase 13.2–13.3) |

---

## 7. Smoke contable

| Verificación | Resultado |
|--------------|-----------|
| Cotización ITBIS 18% | PASS — `[18.0]` |
| Factura B02 publicada | PASS — INV/2026/00003 |
| NCF asignado | PASS — B0200009902 |
| Asiento balanceado | PASS — `sum(balance) ≈ 0` |
| Líneas ITBIS 18% | PASS |
| Cuenta por cobrar | PASS |

---

## Scripts utilizados

| Script | Función |
|--------|---------|
| `scripts/phase13-4-harden-prod.py` | Hardening BD (solo `hellenia_prod`) |
| `scripts/run-phase13-4-harden-prod.sh` | Orquestador + Traefik + evidencia |

---

## Restricciones respetadas

- Sin cambios en core Odoo
- Sin cambios en Enterprise
- Sin tocar `odoo-pecv`
- Sin nuevas funcionalidades de negocio
- Solo `hellenia_prod`

---

**Conclusión:** Producción hardened operativamente. Lista para **carga de datos reales** con pendientes documentados en `FINAL_PENDING_ITEMS.md`.
