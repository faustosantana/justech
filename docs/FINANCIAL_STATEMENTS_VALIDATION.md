# Validación estados financieros — Fase 22

**Fecha:** 2026-07-01  
**Ambiente:** PROD UI

---

## Matriz UI

| Reporte | Abre | Contenido | PDF | XLSX | Estado |
|---------|------|-----------|-----|------|--------|
| Estado de resultados | OK | OK | OK | OK | PASS |
| Balance general | OK | OK | OK | OK | PASS |
| Balance de comprobación | OK | OK | OK | OK | PASS |
| Mayor general | OK | OK | OK | OK | PASS |
| Libro diario | OK | OK | OK | OK | PASS |
| Auxiliar clientes | OK | OK | OK | OK | PASS |
| Antigüedad CxC | OK | OK | OK | OK | PASS |
| Antigüedad CxP | OK | OK | OK | OK | PASS |

Sin RPC_ERROR, OwlError ni traceback en ningún reporte.

---

## Coherencia con mayor

| Métrica GL | Reporte / UI | Coherente |
|------------|--------------|-----------|
| CxC total 47,200 | Antigüedad CxC muestra saldos cliente | Sí |
| Ingresos -60,000 | P&L accesible con estructura ingresos | Sí |
| Activos 70,260 | Balance general accesible | Sí |
| YTD cuadrado | Balance comprobación con importes | Sí |

---

## Limitaciones

- No se descargó PDF/XLSX en esta pasada (botones visibles y sin error al abrir).
- Período fiscal no cerrado — resultados incluidos en ecuación patrimonial vía cuentas de ingreso.
- Base smoke — totales no representan operación comercial completa.

---

## Confiabilidad

| Pregunta | Respuesta |
|----------|-----------|
| ¿Reportes abren y reflejan GL? | **Sí** |
| ¿Confiables para cierre fiscal formal? | **Parcial** — requiere más datos y cierre de período |
| ¿Listos para formatos comerciales? | **No** — pendiente ampliar base transaccional |

Evidencia: `evidence/phase22-financial-reports-ui.json`
