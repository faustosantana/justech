# Fase 21.1 — Regresión final reportes DGII (PROD)

**Fecha:** 2026-07-01  
**Ambiente:** `hellenia_prod` @ `https://odoo.hellenia.cloud`  
**Módulo:** `justech_l10n_do_reports` **19.0.1.12.4**  
**Período probado:** `202607`  
**Resultado:** **PROD PASS**

---

## Alcance

Validar que el fix del 623 (carga de líneas en bandeja de revisión) **no rompió** 606, 607 ni 608.

**No modificado:** pagos, retenciones, conciliación, odoo-pecv.

---

## Resumen ejecutivo

| Reporte | Abre | Carga período | Datos | Exporta | Estado |
|---------|------|---------------|-------|---------|--------|
| **623** | OK | OK | 1 válido P21 / 500.00 | OK `DGII_623_202607.xlsx` | **PASS** |
| **607** | OK | OK (wizard) | 3 ventas válidas | OK | **PASS** |
| **606** | OK | OK (wizard) | 0 compras (esperado) | N/A | **PASS** |
| **608** | OK | OK | 0 anulados (esperado) | N/A | **PASS** |

| Logs PROD (5 min post-prueba) | RPC_ERROR / OwlError / Traceback |
|--------------------------------|----------------------------------|
| | **0 líneas sospechosas** |

---

## 1. Reporte 623 — transacción limpia P21

| Campo | Valor verificado UI |
|-------|---------------------|
| Partner | P21 GOV PROOF UNIQUE |
| RNC | **101733934** |
| Factura | **INV/2026/00006** |
| Pago | **PBNKD/2026/00003** |
| Retención | RET-GOB-5 — **RD$ 500.00** |
| Válidos exportar | **1** (de 3 en revisión — 2 incompletos SMOKE legacy) |

### Flujo UI certificado

1. Wizard 623 → período 202607 → Generar
2. Revisión fiscal → **Cargar período** → 3 documentos
3. **Validar período** → estado validado
4. **Generar Excel DGII** → descarga `DGII_623_202607.xlsx` sin RPC error

Evidencia: `evidence/phase21-1-dgii-reports/screenshots/623-*.png`

---

## 2. Reporte 607 — período actual 202607

| Criterio | Resultado |
|----------|-----------|
| Abre wizard | OK |
| Validar período | OK — sin error |
| Ventas válidas | **3** (incluye INV/2026/00006 jul-2026) |
| Regresión post-fix 623 | **No afectado** |
| Generar Excel DGII | OK — sin RPC error |

---

## 3. Reporte 606 — período actual 202607

| Criterio | Resultado |
|----------|-----------|
| Abre wizard | OK |
| Validar período | OK — sin error |
| Documentos | 0 compras (esperado en PROD) |
| Error / traceback | **Ninguno** |

---

## 4. Reporte 608 — período actual 202607

| Criterio | Resultado |
|----------|-----------|
| Abre y genera revisión | OK |
| Cargar período | OK |
| Documentos | 0 anulados (esperado) |
| Error / traceback | **Ninguno** |

---

## 5. Validación de logs

```
docker logs hellenia-prod-odoo-1 --since 5m | grep RPC_ERROR|OwlError|Traceback
→ 0 coincidencias relevantes
```

---

## Respuestas certificación

| Pregunta | Respuesta |
|----------|-----------|
| **PROD PASS / FAIL** | **PASS** |
| **623 validado** | **Sí** — 1 válido, RNC, factura, monto 500, export Excel |
| **606/607/608 siguen funcionando** | **Sí** |
| **Errores encontrados** | Ninguno en esta regresión |
| **Reportes DGII certificados uso real** | **Sí** — 623 y 607 con export Excel; 606/608 operativos sin error |

---

## Evidencia

| Archivo | Descripción |
|---------|-------------|
| `evidence/phase21-1-dgii-reports-final-regression.json` | Resultado machine-readable |
| `evidence/phase21-1-dgii-reports/screenshots/` | Capturas UI por reporte |
| `scripts/phase21-1-dgii-reports-final-regression.py` | Script Playwright reproducible |

---

## Relación con Fase 21

- Fix 623 v12.4: `_review_lines_623` + `_prepare_line_vals_623`
- Prueba controlada P21: `docs/PHASE21_623_CONTROLLED_PROOF.md`
- Esta regresión confirma que el fix **no introduce regresión** en el resto del módulo DGII.
