# J-10P — Product polish paralelo (señales, gráficas, estados)

**Worktree:** `/Users/faustosantana/Projects/justech-j10-parallel`  
**Rama:** `feature/nr-j10-parallel-product-polish`  
**Base:** `origin/feature/nr-control-center-final-ux-j10` @ `13d72d1`  
**Aislamiento:** no remount DEV · no seeds · no phase_j10 closeout · no hub page

## Matriz de gaps (auditoría)

| Requisito | Estado | Archivo | Cambio |
|-----------|--------|---------|--------|
| SignalCard | ausente | — | Nuevo componente |
| Orden visual determinista | ausente | — | `signal-order.ts` + helper backend |
| 5 gráficas con NL | parcial (8 barras) | historial-numero | `historical-charts.tsx` |
| Why estructurado | parcial (pasos string) | number_explorer | Campos + UI |
| Empty states | parcial | — | `nr-empty-states.tsx` |
| Hub / seed / remount | no tocar | page.tsx hub, j10_seed, servers | — |

## Orden de visualización (no es fuerza oficial)

1. confirmaciones actuales  
2. casos evaluables  
3. rate_within_3  
4. ciclo típico (menor primero)  
5. número ascendente  

## No tocar

- `phase_j10/**` closeout/screenshots  
- `scripts/j10_seed_featured_dev.py`  
- `scripts/j9_nr_dev_server.py`  
- hub `control-center/page.tsx`  
- fórmulas / T1 / T2 / `/analyze` v1  

## Entrega

Commits J-10P.0 … J-10P.5 en esta rama; cherry-pick selectivo tras J-10.5.
