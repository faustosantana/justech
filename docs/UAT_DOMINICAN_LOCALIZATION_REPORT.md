# UAT — Localización Dominicana (Bloque 8)

**Ambiente:** TEST | **Fecha:** 2026-06-30 | **Estado:** **PASS**

## Validaciones fiscales

| Control | Resultado |
|---------|-----------|
| Fiscal habilitado | ✅ |
| 6 tipos documento NCF | ✅ |
| 8 rangos UAT | ✅ |
| Asignación automática NCF | ✅ |
| B01 factura crédito fiscal | ✅ |
| B02 consumo | ✅ |
| B03 nota débito | ✅ |
| B04 nota crédito | ✅ |
| B11/B13 compras | ✅ |
| Void NCF + 608 | ✅ |
| Duplicados bloqueados | ✅ |
| Reporte 606 | ✅ 104 líneas |
| Reporte 607 | ✅ 153 líneas |
| Reporte 608 | ✅ |
| PDF factura | ✅ (warning logo filestore) |
| Concurrencia NCF | ✅ PASS |
| Rango agotado | ✅ Bloqueado |
| Rango vencido | ✅ Bloqueado |
| PHASE6_MVP post-UAT | ✅ 19/19 |

## Observaciones

- Rangos UAT no son autorización DGII real — esperado en TEST
- Asset logo filestore ausente — PDF genera con warning wkhtmltopdf

**Estado:** PASS — área fiscal MVP certificada para piloto

**Evidencia:** `evidence/uat-functional.json`, `evidence/uat-stress.json`, `evidence/uat-audit.json`
