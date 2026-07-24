# PHASE J-10X — Lottery IA Platform Consolidation

**Branch:** `feature/nr-lottery-ai-platform-consolidation`  
**Base:** `feature/nr-j10h-visual-scope-hotfix` @ `0c86e25`  
**Scope:** Frontend UX consolidation only — no formula, UUID, featured policy, historic data, or `/analyze` changes.  
**Deploy:** DEV visual GO required before Production.

---

## J-10X.0 — Route / menu audit matrix

### Problem

Production felt like two apps:

| Shell | Source | Identity |
|-------|--------|----------|
| A — AppShell sidebar | `frontend/src/lib/modules/registry.ts` | “Resultados de Loterías” |
| B — Nested CC nav | `…/control-center/layout.tsx` `NAV` | “Lottery IA · Inteligencia” |
| C — Centro de IA | `…/admin/ai/layout.tsx` | Third admin IA surface |

### Duplicate functions (pre-consolidation)

| Función | Rutas previas | Destino canónico J-10X |
|---------|---------------|------------------------|
| Home | `/lottery`, `/lottery/admin/control-center` | `/lottery` |
| Historial / consulta | `/lottery/search`, `…/motor/historial-numero`, `…/motor/historico` | `…/motor/historial-numero` |
| Comparar | `/lottery/compare`, `…/motor/comparador` | `…/motor/comparador` |
| Estadísticas / matriz | `/lottery/statistics`, `…/motor/combinaciones` | `…/motor/combinaciones` |
| Agrupaciones | `…/groups-table1`, `…/groups-table2` | `…/motor/agrupaciones` (tabs) |
| Relaciones | `…/motor/relaciones`, `/lottery/admin/numeric-relations` | `…/motor/relaciones` |
| Catálogo | `/lottery/lotteries` | unchanged |
| Archivo | `/lottery/admin/lotteries/archivo-historico` | unchanged |

### Access model (chosen)

- Análisis + Motor consulta: all authenticated lottery module users.
- Sync, Scheduler, Prompt Studio, admin Catálogo write, Centro de IA: admin/owner (registry `roles`).

### UX debt addressed

1. Dual sidebar on Control Center routes.
2. Triple lottery checkbox walls (aparición / confirmación / seguimiento).
3. Raw English enums (`SAME_DRAW`, `candidates`) in forms/results.
4. Overlapping labels (Comparar vs Comparador, etc.).

---

## Implementation log

| Phase | Status | Notes |
|-------|--------|-------|
| J-10X.0 Audit | DONE | This matrix |
| J-10X.1 Single sidebar | pending | |
| J-10X.2 Home identity | pending | |
| J-10X.3 Historial | pending | |
| J-10X.4 Comparador | pending | |
| J-10X.5 Agrupaciones / Relaciones | pending | |
| J-10X.6 Auditoría / Admin | pending | |
| J-10X.7 Redirects / mobile | pending | |
| J-10X.8 E2E / verdict | pending | |

---

## Verdict

_Pending DEV browser evidence._
