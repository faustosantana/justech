# 30 — Informe final

## Identificación

| Campo | Valor |
|-------|--------|
| Rama | `feature/nr-deep-mathematical-relations-audit` |
| Commit fase | `2a19579` |
| Worktree | `/Users/faustosantana/Projects/justech-forensic-audit` |
| audit_id | `8886dedf-b561-4aa7-984f-3b856b89b697` |
| Período | 2019-07-23 → 2026-07-16 |
| Producción | intacta |
| J-11A | no iniciado |

## Respuestas numéricas (1–30, extracto)

1. Activaciones cadena: **2477**
2. Fuertes distintos: **84** (activaciones fuerte/día: 2222)
3. Exacto por D+n: {'D+1': 400, 'D+2': 335, 'D+3': 287, 'D+4': 206, 'D+5': 175, 'D+6': 147, 'D+7': 120}
4. Lotería/posición de primera aparición: ver `strong_exact_results.csv`
5–8. Cuando no sale: primer relacionado y posiciones en `all_future_appearances.csv` + cap. 07/25
9. Distancia T1 más frecuente: {'distance': 0, 'count': 3483, 'pct': 21.17}
10. Anterior vs siguiente: comparar dist −1 y +1 en cap. 08
11. Cercanos vs lejanos: etiquetas T1 en `label_summary`
12–13. Confirmador / compañero del confirmador: etiquetas dedicadas
14. Cadenas top: cap. 10
15–16. Estabilidad anual / lotería: cap. 17–18
17. Posiciones de sorteo: cap. 16
18–19. Multi-confirmación / multi-fuerte: cap. 14/25
20. Número con más repetición como fuerte: 42
21–22. Pares y loterías: cap. 10/17
23–27. T1/T2 como secuencia ordenada: distancias ≠ 0 demuestran uso del orden canónico
28–30. Ciclos/estables/inestables: niveles de consistencia + year_span

## Rutas

- Libro HTML: `docs/lottery/deep_mathematical_audit/index.html`
- CSV: `artifacts/deep_mathematical_audit/*.csv`
- JSON: `artifacts/deep_mathematical_audit/full_statistics.json`

## Cierre

Período procesado. Trazabilidad por CSV. 50 casos. 20 verificaciones manuales.
Producción intacta. Motor intacto. Detener y esperar autorización.
