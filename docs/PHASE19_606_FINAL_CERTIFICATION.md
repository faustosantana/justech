# Fase 19.2 — Certificación final 606 TEST

## Alcance

Validar que el exportador 606 es usable en período completo tras exclusión fiscal de data UAT/demo.

**Solo TEST** — sin PROD, sin odoo-pecv, sin promoción.

## Ejecución

```bash
cd /opt/odoo-projects/hellenia
git fetch --all
git checkout cursor/phase19-2-606-error-handling-dd85
git pull
rsync -av repository/custom/ ./custom/
rsync -av repository/scripts/ ./scripts/
bash scripts/run-phase19-2-test.sh
```

## Evidencia

| Archivo | Contenido |
|---------|-----------|
| `evidence/phase19-2-cleanup.json` | Facturas excluidas como UAT/demo |
| `evidence/phase19-2-certification.json` | Checks certificación 19.2 |
| `evidence/phase19-606-full-period.xlsx` | 606 período completo (solo válidos) |
| `evidence/phase19-606-errors.xlsx` | Reporte errores/excluidos/válidos |

## Criterios PASS

- [ ] Exclusión UAT/demo ejecutada (`excluded_count > 0`)
- [ ] Período completo sin incompletos bloqueantes (`incomplete = 0`)
- [ ] Al menos 1 factura válida exportada
- [ ] Excel 606 generado con encabezados y datos fila 12+
- [ ] Resumen validación en español (no lista gigante)
- [ ] Reporte errores Excel descargable
- [ ] Historial fiscal con adjuntos

## Resultado

| Campo | Valor |
|-------|-------|
| **TEST PASS/FAIL** | **PASS 13/13** (2026-06-30 VPS) |
| Facturas excluidas UAT/demo | **111** |
| Facturas válidas en 606 | **37** |
| Incompletos bloqueantes | **0** |
| Excel período completo | `evidence/phase19-606-full-period.xlsx` |
| Reporte errores | `evidence/phase19-606-errors.xlsx` |
| Listo revisión contable | **Sí** — exportador usable; contabilidad debe revisar las 37 válidas |
| Iniciar 607/608 | **Sí, con aprobación contable del 606** — bloqueo UAT resuelto |

### Detalle período junio 2026 (post-limpieza)

| Clasificación | Cantidad |
|---------------|----------|
| Total en período | 148 |
| Válidas exportadas | 37 |
| Excluidas fiscalmente | 111 |
| Incompletas | 0 |
| Anuladas | 0 |
