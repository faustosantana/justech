import { expect, test } from "@playwright/test";

import { apiGet, evidencePath, loadFixtures } from "../helpers/api";

type DocumentItem = {
  id: string;
  title: string;
  metadata: Record<string, unknown>;
};

type DocumentList = { items: DocumentItem[]; total: number };

test.describe("Documents bulk E2E", () => {
  test("selección, export, revisión, tarea, archivar y persistencia", async ({ page }, testInfo) => {
    const fixtures = loadFixtures();
    test.skip(fixtures.document_ids.length < 2, "Sin documentos E2E seed");

    await page.goto("/documents");
    await expect(page.getByTestId("documents-bulk-table")).toBeVisible({ timeout: 30_000 });
    await page.screenshot({ path: evidencePath(testInfo.title, "01-documents-loaded.png"), fullPage: true });

    await page.getByTestId("bulk-select-all").check();
    await expect(page.getByTestId("bulk-selected-count")).toContainText(String(fixtures.document_ids.length));

    const downloadPromise = page.waitForEvent("download");
    await page.getByTestId("bulk-action-export").click();
    const download = await downloadPromise;
    await download.saveAs(evidencePath(testInfo.title, "export.csv"));
    expect(download.suggestedFilename()).toMatch(/\.csv$/i);

    await expect(page.getByTestId("bulk-feedback")).toBeVisible();
    await expect(page.getByTestId("bulk-feedback")).toHaveAttribute("data-feedback-type", "success");
    await page.screenshot({ path: evidencePath(testInfo.title, "02-export-feedback.png"), fullPage: true });

    await page.getByTestId("bulk-action-mark-review").click();
    await expect(page.getByTestId("bulk-feedback")).toContainText(/marcados|revisión/i);

    for (const id of fixtures.document_ids) {
      const doc = await apiGet<DocumentItem>(`/documents/${id}`);
      expect(doc.metadata?.review_flagged_at).toBeTruthy();
    }

    await page.getByTestId("bulk-action-create-task").click();
    await expect(page.getByTestId("bulk-feedback")).toContainText(/tarea/i);

    await page.getByTestId("bulk-clear").click();
    const archiveTarget = fixtures.document_ids[0];
    await page.locator("tr").filter({ hasText: fixtures.e2e_prefix }).first().locator('input[type="checkbox"]').check();
    await page.getByTestId("bulk-action-archive").click();
    await expect(page.getByTestId("bulk-feedback")).toContainText(/archiv/i);

    await page.reload();
    await expect(page.getByTestId("documents-bulk-table")).toBeVisible();
    const listAfter = await apiGet<DocumentList>("/documents?limit=200");
    const activeIds = listAfter.items.map((d) => d.id);
    expect(activeIds).not.toContain(archiveTarget);
    await page.screenshot({ path: evidencePath(testInfo.title, "03-after-reload.png"), fullPage: true });
  });
});
