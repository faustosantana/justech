# PHASE J-10X — Lottery IA Platform Consolidation

**Branch:** `feature/nr-lottery-ai-platform-consolidation`  
**Base:** `feature/nr-j10h-visual-scope-hotfix` @ `0c86e25`  
**Tip (implementation):** see `git log` on branch  
**Scope:** Frontend UX consolidation only — no formula, UUID, featured policy, historic data, or `/analyze` changes.  
**Deploy:** **No Production deploy in this phase.** DEV visual GO recorded below.

---

## Verdict

**GO PARA DESPLIEGUE**

Evidence: DEV browser Playwright capture on `http://127.0.0.1:3012` (worktree Next) + API `http://127.0.0.1:8001` (`jaios_lottery_dev`). Screenshots under [`phase_j10x_visual/screenshots/`](phase_j10x_visual/screenshots/).

---

## J-10X.0 — Route / menu audit matrix

### Problem

Production felt like two apps:

| Shell | Source | Identity |
|-------|--------|----------|
| A — AppShell sidebar | `frontend/src/lib/modules/registry.ts` | “Resultados de Loterías” |
| B — Nested CC nav | `…/control-center/layout.tsx` `NAV` | “Lottery IA · Inteligencia” |
| C — Centro de IA | `…/admin/ai/layout.tsx` | Third admin IA surface |

### Duplicate functions → canonical

| Función | Rutas previas | Destino canónico J-10X |
|---------|---------------|------------------------|
| Home | `/lottery`, `/lottery/admin/control-center` | `/lottery` |
| Historial | `/lottery/search`, `…/historial-numero`, `…/historico` | `…/motor/historial-numero` |
| Comparar | `/lottery/compare`, `…/comparador` | `…/motor/comparador` |
| Estadísticas / matriz | `/lottery/statistics`, `…/combinaciones` | `…/motor/combinaciones` |
| Agrupaciones | `…/groups-table1`, `…/groups-table2` | `…/motor/agrupaciones` (tabs) |
| Relaciones | `…/relaciones`, `/lottery/admin/numeric-relations` | `…/motor/relaciones` |
| Catálogo | `/lottery/lotteries` | unchanged |
| Archivo | `/lottery/admin/lotteries/archivo-historico` | unchanged |

### Access model

- Análisis + Motor consulta: all authenticated lottery module users.
- Sync, Scheduler, Prompt Studio, admin Catálogo, Centro de IA: admin/owner (registry `roles`).

---

## Implementation log

| Phase | Status | Commit theme |
|-------|--------|--------------|
| J-10X.0 Audit | DONE | `docs(lottery): J-10X.0…` |
| J-10X.1 Single sidebar | DONE | registry rewrite; CC layout without nested NAV; open gate |
| J-10X.2 Home identity | DONE | `/lottery` = Control Center; CC index redirects |
| J-10X.3 Historial | DONE | one universe picker; advanced scopes collapsed; ES window labels |
| J-10X.4 Comparador | DONE | shared simplified form; Spanish modes/results |
| J-10X.5 Agrupaciones / Relaciones | DONE | unified tabs + redirects; Relaciones copy |
| J-10X.6 Auditoría / Admin | DONE | Auditoría polish; `lotteryDisplayName` accents UI-only |
| J-10X.7 Redirects / mobile | DONE | page + `next.config` redirects; no Metodología panel |
| J-10X.8 E2E / verdict | DONE | 12 PNG captures; GO |

### Key files

- [`frontend/src/lib/modules/registry.ts`](../../../frontend/src/lib/modules/registry.ts)
- [`frontend/src/app/(platform)/lottery/admin/control-center/layout.tsx`](../../../frontend/src/app/(platform)/lottery/admin/control-center/layout.tsx)
- [`frontend/src/app/(platform)/lottery/page.tsx`](../../../frontend/src/app/(platform)/lottery/page.tsx)
- [`frontend/src/components/lottery/control-center/historical-form.tsx`](../../../frontend/src/components/lottery/control-center/historical-form.tsx)
- [`frontend/src/lib/lottery-display-names.ts`](../../../frontend/src/lib/lottery-display-names.ts)
- [`frontend/next.config.ts`](../../../frontend/next.config.ts)

---

## Acceptance (DEV)

| Criterion | Result |
|-----------|--------|
| One sidebar only; product name **Lottery IA Control Center** | PASS (`01`, `02`, `03`) |
| No nested “Inteligencia / Metodología” nav | PASS (`03`, `12`) |
| Historial / Comparador once each in menu | PASS (`01` sidebar) |
| No triple lottery checkbox walls by default | PASS (`04`, `06`) |
| No raw English enums in primary UI | PASS (`06` — “Mismo sorteo”, “Candidatos (Tabla 1)”) |
| FEATURED_SEVEN / accents in UI | PASS (`01`, `04`, `10` — Lotería Nacional, Gana Más) |
| Legacy `/lottery/search` → historial | PASS (`11`) |
| Mobile without second Metodología panel | PASS (`12`) |
| Formulas / UUIDs / draws untouched | PASS (frontend-only) |

### Screenshots

| File | Subject |
|------|---------|
| `01_home_control_center.png` | Home identity + KPIs = 7 |
| `02_single_sidebar.png` | AppShell IA menu |
| `03_no_dual_nav.png` | Historial without nested nav |
| `04_historial_simple.png` | Single universe picker |
| `05_historial_advanced_collapsed_proof.png` | Advanced scopes available |
| `06_comparador_simple.png` | Spanish modes/labels |
| `07_agrupaciones_tabs.png` | Unified Agrupaciones |
| `08_relaciones.png` | Relaciones entry |
| `09_auditoria.png` | Auditoría polish |
| `10_catalogo_siete.png` | Catálogo seven |
| `11_redirect_search.png` | Legacy search redirect |
| `12_mobile_single_nav.png` | Mobile single nav |

Capture script: [`phase_j10x_visual/capture_screenshots.py`](phase_j10x_visual/capture_screenshots.py)

---

## Out of scope (confirmed)

- Production deploy
- Formula / Tabla methodology / `/analyze` v1
- Featured UUID policy / historic data deletes
- J-11 / new agent
