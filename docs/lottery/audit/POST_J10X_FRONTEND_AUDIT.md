# POST J-10X — Frontend Audit

**Base:** `564a8c0` · 49 lottery `page.tsx` routes

## Identity

- Module label: **Lottery IA Control Center** (`registry.ts`).
- Control Center layout: single `AppShell`, nested NAV removed.
- Groups: Inicio / Análisis / Motor / Avanzado / Administración.

## Findings (prioritized)

### CRÍTICO

**AUD-FE-001 — Third navigation surface `admin/ai`**  
Evidence: [`frontend/src/app/(platform)/lottery/admin/ai/layout.tsx`](../../../frontend/src/app/(platform)/lottery/admin/ai/layout.tsx) — custom `min-h-screen` shell + aside `NAV_GROUPS`, no AppShell.  
Impact: Breaks “one platform / one menu” for AI admin; mobile AppShell collapse bypassed.  
Blocks J-11 UX: **yes** (must integrate copiloto under same shell).

### ALTO

**AUD-FE-002 — `historial-numero/page.tsx` ~976 lines + form duplication**  
Does not use `HistoricalAnalyzerForm` / `HistoryFormState` used by comparador/historico/patron/matriz.

**AUD-FE-003 — Legacy print branding**  
`print/page.tsx` still titles “Resultados de Loterías”.

### MEDIO

**AUD-FE-004 — table1/table2 near-duplicate pages**  
**AUD-FE-005 — Six zombie redirect page files** (also covered by `next.config` redirects)  
**AUD-FE-006 — `admin/ai` alert double-fetch** (layout + page)  
**AUD-FE-007 — `historical-form.tsx` 409 lines** (borderline oversized)

### BAJO / MEJORA

- Widespread `Record<string, unknown>` instead of DTOs.
- `SAME_DRAW` literal in `auditoria/page.tsx` (API value OK; prefer shared constant).
- Inconsistent `min-h-11` touch targets across motor pages.
- Breakpoint `min-[769px]` vs AppShell `md` (768).

## Strengths

- No raw `any` in lottery FE.
- 100% `apiClient` (no scattered `fetch` in lottery pages).
- Spanish labels via `nr-labels.ts` / `lottery-display-names.ts`.
- Simplified Historial/Comparador UX from J-10X.

## API call concentration

~173 `apiClient` calls in lottery pages; hottest: historial-numero (10), admin/ai dashboard.
