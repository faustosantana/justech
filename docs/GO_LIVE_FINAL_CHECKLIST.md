# Go-Live Final Checklist — Hellenia

**Fecha actualización:** 2026-06-30 (Fase 16)  
**URL:** https://odoo.hellenia.cloud  
**Estado global:** **NO LISTO** para apertura a usuarios operativos

---

## Bloqueantes P0 (deben ser PASS antes de Go-Live)

| # | Ítem | Estado | Evidencia / Acción |
|---|------|--------|-------------------|
| P0-1 | Backup producción reciente | **PASS** | `backups/hellenia-prod/2026-06-30_1811` |
| P0-2 | HTTPS / login operativo | **PASS** | Fase 15 healthcheck |
| P0-3 | Menús y navegación ERP | **PASS** | Fase 15 certificación |
| P0-4 | Logo empresa en PDFs | **PASS** | `res.company.logo` presente |
| P0-5 | Rangos NCF DGII reales (B01–B13) | **FAIL** | Entregar `ncf_rangos_dgii.csv` |
| P0-6 | Usuarios operativos ROLE_MATRIX | **FAIL** | Entregar `users.csv` |
| P0-7 | SMTP corporativo probado | **FAIL** | Configurar `.env` + prueba envío |
| P0-8 | Limpiar facturas smoke P13.4 | **FAIL** | Requiere B04 o reversión contador |
| P0-9 | Licencia Odoo EE | Verificar | Registrar si no activa |

---

## Requeridos P1 (operación real)

| # | Ítem | Estado |
|---|------|--------|
| P1-1 | Catálogo productos real | **FAIL** — `productos.csv` |
| P1-2 | Clientes reales | **FAIL** — `clientes.csv` |
| P1-3 | Proveedores reales | **FAIL** — `proveedores.csv` |
| P1-4 | Existencias iniciales | **FAIL** — `existencias.csv` (opcional) |
| P1-5 | Cuentas bancarias / diarios banco | Pendiente contador |
| P1-6 | Términos de pago comerciales | Pendiente Hellenia |
| P1-7 | UAT con usuarios reales | Pendiente post-importación |

---

## Validación funcional post-carga

Ejecutar tras completar P0:

| Flujo | Script / verificación |
|-------|----------------------|
| Cotización → pedido → entrega → factura B01/B02 | `phase16-go-live-prod.py` validación |
| Cobro cliente | UAT manual |
| Compra → recepción → factura B11 | UAT manual |
| Nota crédito B04 / débito B03 | `validate-phase6-mvp.sh` |
| Reportes 606/607/608 | Menú Contabilidad → Reportes DGII |
| PDF corporativo | Factura con logo + NCF |

---

## Orden de ejecución

1. Hellenia entrega CSVs + SMTP a Justech  
2. `bash scripts/run-phase16-prod.sh` (backup + importación)  
3. Contador valida rangos NCF y limpia facturas smoke  
4. UAT por rol (1 día por área)  
5. Apertura usuarios `@helleniadr.com`  
6. Deshabilitar `admin` para uso rutinario  

---

## Criterio Go-Live

**LISTO** cuando todos los P0 = PASS y al menos P1-1 a P1-3 completados.

**Estado actual:** 4/9 P0 PASS → **NO ABRIR A USUARIOS REALES**
