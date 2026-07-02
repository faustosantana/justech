# Certificación Go-Live Ready — Hellenia Producción

**Fecha:** 2026-06-30 (UTC)  
**Instancia:** https://odoo.hellenia.cloud (`hellenia_prod`)  
**Fases completadas:** 13.2 (fiscal) · 13.3 (validación manual) · 13.4 (hardening)  
**Go-Live ejecutado:** NO

---

## Certificación

# PASS CON OBSERVACIONES

La plataforma técnica y fiscal está **lista para recibir datos reales de Hellenia**.  
El **Go-Live a usuarios finales** permanece **pendiente** hasta cerrar ítems P0.

---

## Matriz de certificación

| Área | Criterio | Estado |
|------|----------|--------|
| Infraestructura HTTPS | `odoo.hellenia.cloud` 200 OK | **PASS** |
| WebSocket / notificaciones | Traefik → 8072, 0 errores | **PASS** |
| Plan contable RD | 288 cuentas, plan `do` | **PASS** |
| Impuestos ITBIS | 18% venta, 0% activo al 15% | **PASS** |
| Localización Justech | Base + NCF + Reportes | **PASS** |
| Menú operativo español | 6 apps + Configuración | **PASS CON OBS.** |
| Sin datos UAT | 0 partners/productos UAT | **PASS** |
| Rangos NCF producción | Rangos DGII reales | **FAIL** — P0 |
| Usuarios Hellenia | Solo admin + it@justech | **FAIL** — P0 |
| SMTP operativo | Envío correo real | **FAIL** — P0 |
| Maestros negocio | Catálogo, clientes, proveedores | **FAIL** — P1 |
| Facturas smoke limpias | INV/2026/00001–00003 | **FAIL** — P0 |

---

## Riesgos

### P0 — Bloqueantes Go-Live

| ID | Riesgo | Impacto | Mitigación |
|----|--------|---------|------------|
| P0-R1 | Sin rangos NCF DGII reales | Facturas sin validez fiscal | Cargar autorizaciones DGII antes de operar |
| P0-R2 | Sin usuarios operativos | Solo acceso técnico | Importar usuarios ROLE_MATRIX |
| P0-R3 | Sin SMTP | No envío facturas/cotizaciones | Configurar servidor correo Hellenia |
| P0-R4 | Facturas smoke en BD | Contaminación contable inicial | Reversar/eliminar INV/2026/00001–00003 |

### P1 — Importantes pre-operación

| ID | Riesgo | Impacto | Mitigación |
|----|--------|---------|------------|
| P1-R1 | Sin catálogo productos | No se puede vender | Importar productos |
| P1-R2 | Sin clientes/proveedores | No operación comercial | Importar contactos |
| P1-R3 | Sin bancos configurados | No conciliación | Parametrizar diarios banco |
| P1-R4 | Menú Apps visible para admin | Confusión UX técnica | Aceptable para admin; ocultar si se desea |

### P2 — Mejoras

| ID | Riesgo | Impacto | Mitigación |
|----|--------|---------|------------|
| P2-R1 | Nombres impuestos en inglés | Cosmético | Etiquetas personalizadas |
| P2-R2 | Formato DGII export MVP | Reporte manual complementario | Roadmap TD-008 |
| P2-R3 | Monitoreo alertas | Detección tardía fallos | Cron healthcheck existente |

---

## Respuestas directas

### ¿Producción lista para cargar datos reales?

# SÍ

La instancia está hardened: fiscalidad correcta, menú limpio, websocket operativo, sin residuos UAT. Proceder con importación de maestros y rangos NCF según `FINAL_PENDING_ITEMS.md`.

### ¿Producción lista para Go-Live?

# NO

Faltan: rangos NCF reales, usuarios Hellenia, SMTP, limpieza facturas smoke, y maestros de negocio.

---

## Evidencia

| Documento | Contenido |
|-----------|-----------|
| `docs/PRODUCTION_HARDENING_REPORT.md` | Detalle Fase 13.4 |
| `docs/PHASE13_3_PRODUCTION_MANUAL_VALIDATION.md` | Validación manual |
| `docs/PRODUCTION_TAX_AND_REPORTS_FIX.md` | Corrección fiscal |
| `docs/FINAL_PENDING_ITEMS.md` | Lista única pendientes |
| `evidence/phase13-4-hardening-prod.json` | JSON hardening |
| `backups/hellenia-prod/2026-06-30_1618` | Backup pre-hardening |

---

## Recomendación final

1. **Ahora:** Iniciar carga de datos reales (rangos NCF, productos, contactos, usuarios) en `hellenia_prod`.
2. **Antes de Go-Live:** Cerrar los 4 ítems P0 de `FINAL_PENDING_ITEMS.md`.
3. **UAT final:** Sesión con usuario clave Hellenia + contador (cotización → factura B01 → reporte 607).
4. **Go-Live:** Solo tras UAT firmado y backup verificado.

No se recomienda abrir el sistema a usuarios finales hasta completar P0. La inversión en Fases 13.2–13.4 dejó la **base técnica certificada**; el siguiente paso es **datos del negocio**, no más desarrollo.

---

**Emitido por:** Cloud Agent — Fase 13.4  
**Estado:** PASS CON OBSERVACIONES — plataforma lista para parametrización; Go-Live pendiente P0
