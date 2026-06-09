import { expect, test } from "@playwright/test";

import { apiGet, evidencePath, loadFixtures } from "../helpers/api";

type DraftItem = {
  id: string;
  status: string;
  task_id: string | null;
  user_id?: string | null;
};

type DraftList = { items: DraftItem[]; total: number };

type AdminUser = { id: string; full_name: string; email: string };

type AdminUserList = { items: AdminUser[] };

type UserCompanies = {
  visible_company_ids: number[];
  default_company_id: number | null;
  available_companies: { id: number; name: string; selected: boolean }[];
};

test.describe("Price Drafts bulk E2E", () => {
  test("asignar, estado, tarea, export, descartar y persistencia", async ({ page }, testInfo) => {
    const fixtures = loadFixtures();
    test.skip(fixtures.draft_ids.length < 2, "Sin borradores E2E seed (requiere producto cotizable indexado)");

    await page.goto("/prices/drafts");
    await expect(page.getByTestId("drafts-bulk-table")).toBeVisible({ timeout: 30_000 });
    await page.screenshot({ path: evidencePath(testInfo.title, "01-drafts-loaded.png"), fullPage: true });

    await page.getByTestId("bulk-select-all").check();
    await expect(page.getByTestId("bulk-selected-count")).toContainText(String(fixtures.draft_ids.length));

    await page.getByText("Vendedor para asignación").locator("..").getByRole("button").first().click();
    await page.getByPlaceholder("Buscar por nombre o correo").fill("Marieli");
    await page.getByRole("button", { name: /Marieli/i }).first().click();

    await page.getByTestId("bulk-action-assign").click();
    await expect(page.getByTestId("bulk-feedback")).toContainText(/vendedor|asignad/i);

    const afterAssign = await apiGet<DraftList>("/prices/quote-drafts");
    for (const id of fixtures.draft_ids) {
      const draft = afterAssign.items.find((d) => d.id === id);
      expect(draft?.user_id).toBe(fixtures.marieli_user_id);
    }

    await page.getByTestId("bulk-select-all").check();
    await page.selectOption("select", "listo_para_odoo");
    await page.getByTestId("bulk-action-status").click();
    await expect(page.getByTestId("bulk-feedback")).toContainText(/estado/i);

    const afterStatus = await apiGet<DraftList>("/prices/quote-drafts");
    for (const id of fixtures.draft_ids) {
      const draft = afterStatus.items.find((d) => d.id === id);
      expect(draft?.status).toBe("listo_para_odoo");
    }

    await page.getByTestId("bulk-select-all").check();
    const downloadPromise = page.waitForEvent("download");
    await page.getByTestId("bulk-action-export").click();
    const download = await downloadPromise;
    await download.saveAs(evidencePath(testInfo.title, "drafts-export.csv"));

    await page.getByTestId("bulk-select-all").check();
    await page.getByTestId("bulk-action-create-task").click();
    await expect(page.getByTestId("bulk-feedback")).toContainText(/tarea/i);

    await page.getByTestId("bulk-select-all").check();
    await page.getByTestId("bulk-action-discard").click();
    await expect(page.getByTestId("bulk-feedback")).toContainText(/descart/i);

    await page.reload();
    await expect(page.getByTestId("drafts-bulk-table")).toBeVisible();
    const afterReload = await apiGet<DraftList>("/prices/quote-drafts");
    for (const id of fixtures.draft_ids) {
      const draft = afterReload.items.find((d) => d.id === id);
      expect(draft?.status).toBe("descartado");
    }
    await page.screenshot({ path: evidencePath(testInfo.title, "02-after-reload.png"), fullPage: true });
  });
});

test.describe("Admin empresas E2E", () => {
  test("cambiar empresas, default, guardar y persistencia API", async ({ page }, testInfo) => {
    const fixtures = loadFixtures();
    test.skip(!fixtures.marieli_user_id, "Usuario Marieli no disponible en seed");

    const users = await apiGet<AdminUserList>("/admin/users");
    const marieli = users.items.find((u) => u.id === fixtures.marieli_user_id);
    expect(marieli).toBeTruthy();

    await page.goto("/admin/usuarios");
    await expect(page.getByText("Usuarios")).toBeVisible();
    await page.getByTestId(`admin-companies-btn-${fixtures.marieli_user_id}`).click();
    await expect(page.getByTestId("admin-companies-panel")).toBeVisible();
    await page.screenshot({ path: evidencePath(testInfo.title, "01-panel-open.png"), fullPage: true });

    const before = await apiGet<UserCompanies>(`/admin/users/${fixtures.marieli_user_id}/companies`);
    const companies = before.available_companies;
    test.skip(companies.length < 2, "Se requieren al menos 2 empresas Odoo para probar toggles");

    const first = companies[0];
    const second = companies[1];
    const targetVisible = [first.id, second.id];

    await page.getByTestId(`admin-company-check-${first.id}`).setChecked(true);
    await page.getByTestId(`admin-company-check-${second.id}`).setChecked(true);
    await page.getByTestId(`admin-company-default-${second.id}`).check();

    await page.getByTestId("admin-companies-save").click();
    await expect(page.getByTestId("admin-companies-save-success")).toBeVisible();

    const afterSave = await apiGet<UserCompanies>(`/admin/users/${fixtures.marieli_user_id}/companies`);
    expect(afterSave.visible_company_ids.sort()).toEqual(targetVisible.sort());
    expect(afterSave.default_company_id).toBe(second.id);

    await page.reload();
    await page.getByTestId(`admin-companies-btn-${fixtures.marieli_user_id}`).click();
    await expect(page.getByTestId(`admin-company-check-${first.id}`)).toBeChecked();
    await expect(page.getByTestId(`admin-company-check-${second.id}`)).toBeChecked();
    await expect(page.getByTestId(`admin-company-default-${second.id}`)).toBeChecked();

    const afterReload = await apiGet<UserCompanies>(`/admin/users/${fixtures.marieli_user_id}/companies`);
    expect(afterReload.default_company_id).toBe(second.id);
    await page.screenshot({ path: evidencePath(testInfo.title, "02-after-reload.png"), fullPage: true });
  });
});
