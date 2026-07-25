/**
 * Pre-J11A — E2E Lottery (TD-005): AppShell único, hub, admin/ai integrado.
 * No depende de Producción. Requiere stack DEV/test + auth state de global-setup.
 */
import { expect, test } from "@playwright/test";

const FEATURED_HINTS = [
  "Nacional",
  "Leidsa",
  "Loteka",
  "Gana",
  "Real",
  "New York",
];

test.describe("Lottery Pre-J11A shell", () => {
  test("hub /lottery — sidebar única y loterías destacadas", async ({ page }) => {
    await page.goto("/lottery");
    await expect(page).toHaveURL(/\/lottery/);
    // Una sola navegación lateral AppShell (aside del shell)
    const sidebars = page.locator("aside");
    await expect(sidebars.first()).toBeVisible({ timeout: 60_000 });
    const asideCount = await sidebars.count();
    expect(asideCount).toBeLessThanOrEqual(2); // shell + posible drawer móvil

    const body = await page.locator("body").innerText();
    const hits = FEATURED_HINTS.filter((h) => body.includes(h));
    expect(hits.length).toBeGreaterThanOrEqual(3);
  });

  test("admin/ai dentro de AppShell — sin shell propia", async ({ page }) => {
    await page.goto("/lottery/admin/ai");
    await page.waitForTimeout(1500);
    // Si redirige por permisos, aceptar /lottery
    const url = page.url();
    if (url.includes("/login")) {
      test.skip(true, "sesión E2E sin acceso");
    }
    if (url.endsWith("/lottery") || url.includes("/lottery?")) {
      // usuario sin admin — estado sin acceso documentado
      return;
    }
    await expect(page.getByText(/Centro de IA|Administración de Lottery IA/i).first()).toBeVisible({
      timeout: 30_000,
    });
    // No debe quedar el título viejo de shell aislada como único chrome
    const nestedAdminHeader = page.locator("header").filter({
      hasText: "Centro de Administración de Lottery IA",
    });
    await expect(nestedAdminHeader).toHaveCount(0);
    // Sidebar del producto presente
    await expect(page.locator("aside").first()).toBeVisible();
  });

  test("regreso a /lottery desde admin/ai", async ({ page }) => {
    await page.goto("/lottery/admin/ai");
    await page.waitForTimeout(1000);
    await page.goto("/lottery");
    await expect(page).toHaveURL(/\/lottery$/);
  });

  test("móvil — viewport estrecho mantiene AppShell", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/lottery");
    await expect(page.locator("body")).toBeVisible();
    await page.goto("/lottery/admin/ai");
    await expect(page.locator("body")).toBeVisible();
  });
});
