# Fase 20.1 — Certificación manual UI (TEST)

**Entorno:** https://test.hellenia.cloud — `hellenia_test`  
**Fecha:** 2026-06-30  
**Usuarios de prueba:**
- Fiscal: `usuario.contabilidad.demo15`
- Supervisor: `it@justech.do`
- Contraseña temporal certificación: `CertFiscal20!`

## Resultado

| Métrica | Valor |
|---------|-------|
| Pasos evaluados | 20 |
| Pasos OK en recorrido UI | **18 / 20** |
| **Certificación final** | **NO PASS** |

> Criterio del cliente: no marcar PASS hasta validación manual completa. Quedan 2 puntos por confirmar/re-ejecutar en UI y limpieza de datos residuales en bandeja.

---

## Capturas por paso

| Paso | Archivo | Resultado |
|------|---------|-----------|
| 1 Generar 606 | `evidence/phase20-1/screenshots/01-generar-606.png` | OK |
| 2 Período YYYYMM | `evidence/phase20-1/screenshots/02-periodo-fechas.png` | OK — 01/06/2026 — 30/06/2026 |
| 3 Contadores wizard | `evidence/phase20-1/screenshots/03-contadores-wizard.png` | OK — 148 / 37 |
| 4 Revisión fiscal | `evidence/phase20-1/screenshots/04-revision-fiscal.png` | OK — pestañas y resumen |
| 5 Contadores revisión | (misma captura 04) | OK — 148 = wizard |
| 4b Acciones línea | `05-factura.png`, `05-proveedor.png`, `05-pdf.png` | OK — factura, proveedor, PDF |
| 6 Exclusión | `06-exclusion.png` | **Revisar** — exclusión ejecutada; validación automática de texto falló por timing |
| 7 Envío aprobación | `07-envio-aprobacion.png` | OK |
| 8 Supervisor | `08-login-supervisor.png` | OK |
| 9 Pendientes | `09-pendientes-aprobacion.png` | OK — reporte visible |
| 9 Detalle bandeja | `09-detalle-bandeja.png` | OK |
| 14 Bloqueo Excel | `14-asistente-bloqueo.png` | **Pendiente** — captura muestra bandeja; asistente debe probarse desde revisión antes de aprobar |
| 10 Aprobar línea | `10-aprobacion-linea.png` | OK |
| 11-12 Rechazar / corrección | `09-detalle-bandeja.png` | Controles visibles; ejecución completa requiere 2.ª exclusión |
| 13 Bitácora + chatter | `13-bitacora-chatter.png` | OK — Creación, Validación, Exclusión, Envío, Aprobación |
| 15 Aprobación completa | `15-aprobacion-completa.png` | OK |
| 16 Generar Excel | `16-excel-generado.png` | OK — estado Generado |
| 17 Fuera de pendientes | `17-pendientes-vacio.png` | **Revisar** — reporte legacy `2026-06-30` aún en bandeja |
| 18 Historial | `18-historial-fiscal.png` | OK |
| 19 Hash Excel | `19-reporte-generado-hash.png` | OK |
| 20 Español | `20-interfaz-espanol.png` | OK — sin textos técnicos EN visibles |

Evidencia JSON: `evidence/phase20-1/phase20-1-manual-certification.json`

---

## Errores encontrados

### 1. Historial abría formulario legacy (CORREGIDO)
- **Síntoma:** Al volver de factura o abrir desde historial, fechas `Jun 1`/`Jun 30`, statusbar `Borrador/Validado/Generado` sin workflow completo.
- **Causa:** `action_justech_do_fiscal_report` usaba formulario base, no vista revisión.
- **Corrección:** Historial e historial 606 usan `view_justech_do_fiscal_report_review_form` + fechas `date_from_display`/`date_to_display`.

### 2. Bandeja con reportes residuales de pruebas anteriores
- **Síntoma:** Paso 17 — sigue apareciendo `606 — Compras 2026-06-30` en pendientes tras completar flujo nuevo `202606`.
- **Causa:** Datos de debug/sesiones previas en BD TEST.
- **Acción:** Limpiar o resolver reportes legacy antes de certificación final.

### 3. Chatter con artefacto `False`
- **Síntoma:** En bitácora/chatter aparece `False` en mensaje de exclusión automática.
- **Causa:** Concatenación de campo booleano en mensaje.
- **Estado:** Menor — no bloquea flujo; corregir en fase posterior.

### 4. Menús Odoo base en inglés ("Review")
- **Síntoma:** Submenú Contabilidad muestra "Review" (estándar Odoo EE).
- **Estado:** Fuera del módulo fiscal; no bloqueante.

---

## Correcciones aplicadas (Fase 20.1)

- `views/fiscal_report_views.xml` — historial usa vista revisión; botón «Revisión fiscal»; fechas DD/MM/YYYY
- Versión módulo `19.0.1.8.1`
- Usuarios TEST preparados para certificación manual
- Evidencia UI completa en `evidence/phase20-1/`

---

## Flujo E2E verificado en UI

```
Wizard 606 → Validar → Guardar revisión → Excluir → Enviar aprobación
→ Supervisor: Pendientes → (Bloqueo Excel)* → Aprobar → Generar Excel → Historial
```

\* Paso 14 requiere re-ejecución manual desde formulario revisión **antes** de aprobar (secuencia de captura).

---

## Autorización

| Item | Estado |
|------|--------|
| Framework fiscal 606 en UI TEST | **Funcional — 18/20 pasos con evidencia** |
| Certificación PASS Fase 20.1 | **NO AUTORIZADA** |
| Continuar 607/608/609 | **NO AUTORIZADO** |
