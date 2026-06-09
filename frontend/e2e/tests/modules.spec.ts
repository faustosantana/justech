import { expect, test } from "@playwright/test";

import { apiGet, apiPost, evidencePath } from "../helpers/api";

type TaskItem = { id: string; title: string; status: string };
type TaskList = { items: TaskItem[]; total: number };

test.describe("Tasks bulk E2E", () => {
  test("crear tarea, seleccionar, archivar y persistencia", async ({ page }, testInfo) => {
    const title = `E2E-QA-task-${Date.now()}`;
    const created = await apiPost<TaskItem>("/tasks", { title, description: "Tarea E2E QA autónoma" });

    await page.goto("/tasks");
    await expect(page.getByRole("table")).toBeVisible({ timeout: 30_000 });
    await page.getByPlaceholder(/buscar/i).fill(title);
    await page.waitForTimeout(800);
    await page.locator("tr").filter({ hasText: title }).locator('input[type="checkbox"]').check();
    await expect(page.getByTestId("bulk-selected-count")).toContainText("1");
    await page.screenshot({ path: evidencePath(testInfo.title, "01-task-selected.png"), fullPage: true });

    await page.getByTestId("bulk-action-archive").click();
    await expect(page.getByTestId("bulk-feedback")).toContainText(/archiv/i);

    await page.reload();
    const tasks = await apiGet<TaskList>(`/tasks?search=${encodeURIComponent(title)}&limit=20`);
    const task = tasks.items.find((t) => t.id === created.id);
    expect(task?.status).toBe("cancelada");
    await page.screenshot({ path: evidencePath(testInfo.title, "02-after-archive.png"), fullPage: true });
  });
});

test.describe("Prices E2E", () => {
  test("buscar productos y ver resultados", async ({ page }, testInfo) => {
    await page.goto("/prices");
    await expect(page.getByText("Buscador comercial")).toBeVisible({ timeout: 30_000 });
    await page.getByPlaceholder("Ej. laptop i5 16GB 512GB SSD").fill("Dell");
    await page.getByRole("button", { name: /^Buscar$/i }).click();
    await page.waitForTimeout(2000);
    const api = await apiGet<{ total: number; items: unknown[] }>("/prices/search?q=Dell&limit=5");
    expect(api.total).toBeGreaterThan(0);
    await expect(page.locator("table tbody tr, .rounded-lg.border").first()).toBeVisible();
    await page.screenshot({ path: evidencePath(testInfo.title, "01-prices-search.png"), fullPage: true });
  });
});

test.describe("DGCP E2E", () => {
  test("dashboard carga KPIs y tabla de oportunidades", async ({ page }, testInfo) => {
    await page.goto("/dgcp");
    await expect(page.getByText(/oportunidades|DGCP|licitaciones/i).first()).toBeVisible({ timeout: 30_000 });
    await expect(page.locator("table, [data-testid='dgcp-opportunities']").first()).toBeVisible();
    await page.screenshot({ path: evidencePath(testInfo.title, "01-dgcp-dashboard.png"), fullPage: true });

    const dashboard = await apiGet<{ total_opportunities: number }>("/dgcp/dashboard");
    expect(dashboard.total_opportunities).toBeGreaterThanOrEqual(0);
  });
});

test.describe("Search E2E", () => {
  test("búsqueda enterprise devuelve resultados en UI", async ({ page }, testInfo) => {
    await page.goto("/search");
    const input = page.getByPlaceholder("Buscar clientes, productos, facturas, licitaciones, tareas…");
    await input.fill("Banco");
    await page.getByRole("button", { name: /^Buscar$/i }).click();
    await page.waitForTimeout(2500);
    await expect(page.getByText(/resultado\(s\) para/i)).toBeVisible({ timeout: 20_000 });
    await page.screenshot({ path: evidencePath(testInfo.title, "01-search-results.png"), fullPage: true });

    const api = await apiGet<{ total: number }>("/search?q=Banco&limit=5");
    expect(api.total).toBeGreaterThan(0);
  });
});
