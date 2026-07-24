# PHASE J-10H — Visual Scope Hotfix Report

**Fecha (UTC):** 2026-07-24  
**Veredicto:** **PRODUCCIÓN CORREGIDA VISUALMENTE**  
**URL:** https://jaios.justech.do  
**Commits:** `2d60793`, `2d2ad3b` (`feature/nr-j10h-visual-scope-hotfix`)  
**Imagen:** `jaios-app-*:j10h-seven-lotteries-visual-hotfix-20260724`

---

## 1. Causa raíz

J-10F fijó `is_featured` para el motor NR (`/numeric-relations/*`), pero el hub ordinario y el catálogo **no** usaban ese criterio.

| Pantalla | Endpoint | Filtro anterior (incorrecto) | Filtro correcto (J-10H) |
|----------|----------|------------------------------|-------------------------|
| `/lottery` KPIs | `GET /lottery/dashboard/v3` | `active` / `is_visible` / sync (inventario ~49) | `is_featured=true` |
| Catálogo | `GET /lottery/catalog` | visible+catalog (~49) | `is_featured=true` por defecto |
| Selectores / search módulo | `GET /lottery/lotteries` | searchable sin featured | `featured_only=true` |
| Admin lista “normal” | `GET /lottery/admin/lotteries` | sin filtro | `featured=true` |
| Archivo histórico | admin `featured=false` | (nuevo uso) | no destacadas |
| NR analyze | (J-10F) | ya featured | sin cambio metodológico |

Por eso la API NR decía 7 y el navegador seguía mostrando **49**.

---

## 2. Componentes modificados

**Backend**

- `backend/app/services/lottery_admin_service.py` — `_PRODUCT_SCOPE`, dashboard/catalog/admin
- `backend/app/services/lottery_service.py` — list selectors
- `backend/app/api/v1/lottery.py` — params `featured` / `include_archived`
- `backend/tests/test_lottery_j10h_visual_scope.py`

**Frontend**

- `frontend/src/app/(platform)/lottery/page.tsx` — Centro de Inteligencia (7 tarjetas + bloques)
- `.../lotteries/page.tsx` — catálogo solo activas
- `.../admin/lotteries/page.tsx` — solo 7 + link archivo
- `.../admin/lotteries/archivo-historico/page.tsx` — tabla archivadas
- `frontend/src/lib/api.ts` — params featured

---

## 3. Caché / build

| Ítem | Valor |
|------|--------|
| Backend digest | `sha256:bf4232b49f2d…` tag `j10h-seven-lotteries-visual-hotfix-20260724` |
| Frontend digest | `sha256:fb7b43fda072…` |
| Next BUILD_ID | `cvNWoc9i4Tl7tLu5uXNi2` |
| `/lottery` | HTTP 200; `x-powered-by: Next.js` |
| Rollback tags | `rollback-pre-j10h-20260724` (+ `rollback-pre-j10f-20260724` intacto) |
| Backup | `/var/jaios/backups/pre_j10h_20260724_225450/` dump SHA `0908a241…` |

Rebuild FE + recreate contenedores invalida bundle anterior. No service worker propio detectado.

---

## 4. DEV

- Dashboard v3: active=7, visible=7, expected=7  
- Catalog total=7; búsqueda “Loto Leidsa”/“Anguila” → 0  
- Admin featured=7; archived=42  
- (DEV sin tabla `lottery_sources`: tolerancia añadida en v3)

---

## 5. Producción — API

```
active=7 visible=7 expected=7 pending_visible=7
catalog_total=7
search_loto=0
admin_featured=7 admin_archived=42
selector_total=7
draws=91937
```

Nombres catálogo: Loteria Nacional, Quiniela Leidsa, Quiniela Loteka, Gana Mas, Quiniela Real, New York 2:30, New York 10:30.

---

## 6. Producción — navegador (fuente de verdad)

Capturas en `phase_j10h_visual/screenshots/`:

| Archivo | Evidencia |
|---------|-----------|
| `01_dashboard_only_seven.png` | Título “Centro de Inteligencia…”; Activas 7; Visibles 7; Esperados 7; 7 tarjetas; **sin 49** |
| `02_catalog_only_seven.png` | “7 lotería(s) activas”; solo las siete |
| `02b_admin_lotteries_seven.png` | “Mostrando 7 activas” |
| `03_archived_catalog.png` | Archivo administrativo con inventario histórico |
| `04_search_archived_hidden.png` | Buscar “Loto Leidsa” → **0** + “No hay loterías…” |
| `05_mobile_only_seven.png` | Mismo hub en móvil |

Playwright VERDICT: `title=true, no49=true, catalog7=true, search0=true`.

---

## 7. Históricos

- Draws: **91937** (sin pérdida)  
- Ninguna lotería borrada  
- Fórmulas / Tabla 1–2 / `/analyze` v1 / UUIDs: no alterados  

---

## 8. Rollback

```bash
cd /opt/jaios-app
# pin docker-compose.harden.yml → rollback-pre-j10h-20260724
docker compose -f docker-compose.yml -f docker-compose.harden.yml up -d backend frontend lottery-sync-worker
docker compose -f docker-compose.yml -f docker-compose.harden.yml restart gateway
```

---

## 9. Veredicto final

### PRODUCCIÓN CORREGIDA VISUALMENTE

El navegador de Producción muestra siete loterías, catálogo ordinario sin 49, búsqueda de archivadas vacía, hub reorganizado y archivo histórico separado.

**No iniciar J-11** hasta cierre formal de este hotfix.
