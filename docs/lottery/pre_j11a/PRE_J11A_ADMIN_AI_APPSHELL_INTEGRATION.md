# Pre-J11A — Integración admin/ai → AppShell (TD-002)

## Antes

`frontend/src/app/(platform)/lottery/admin/ai/layout.tsx` renderizaba:

- header propio (“Centro de Administración de Lottery IA”)
- `<aside>` de navegación IA
- `<main>` independiente

→ tercera shell visual vs Lottery IA Control Center.

## Después

Mismo patrón que Control Center (`admin/control-center/layout.tsx`):

- Un solo `AppShell` (sidebar + header de producto)
- Navegación secundaria de IA como **tira in-content** (chips/links), no aside
- Rutas `/lottery/admin/ai/**` intactas
- Permisos / redirect a `/lottery` sin cambios
- `LotteryAIDevModeProvider` conservado

## Identidad

Producto: **Lottery IA Control Center**  
Sección: Centro de IA (admin)

## Pruebas

- E2E: `e2e/tests/lottery-pre-j11a.spec.ts`
- Manual: sidebar única, desktop/tablet/móvil, sin acceso, regreso a `/lottery`
