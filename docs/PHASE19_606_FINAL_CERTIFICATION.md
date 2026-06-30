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
| TEST PASS/FAIL | _(actualizar tras ejecución VPS)_ |
| Facturas excluidas UAT/demo | _(excluded_count)_ |
| Facturas válidas en 606 | _(valid count)_ |
| Listo revisión contable | _(sí/no + reservas)_ |
| Iniciar 607/608 | _(sí/no)_ |

Actualizar esta tabla al completar `run-phase19-2-test.sh` en VPS.
