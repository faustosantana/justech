import { expect, type Page } from "@playwright/test";

/** Selecciona filas por IDs de fixture (estable aunque existan duplicados archivados). */
export async function selectRowsByIds(
  page: Page,
  rowIds: string[],
): Promise<void> {
  for (const id of rowIds) {
    const checkbox = page
      .getByTestId(`bulk-row-${id}`)
      .locator('input[type="checkbox"]:enabled');
    await expect(checkbox).toBeVisible({ timeout: 30_000 });
    await checkbox.check({ force: true });
  }
  await expect(page.getByTestId("bulk-selected-count")).toContainText(String(rowIds.length));
}

/** Selecciona filas por prefijo E2E que tengan checkbox activo (excluye descartados/archivados). */
export async function selectRowsWithCheckboxes(
  page: Page,
  prefix: string,
  expectedCount: number,
  rowIds?: string[],
): Promise<void> {
  if (rowIds?.length) {
    await selectRowsByIds(page, rowIds);
    return;
  }

  const checkboxes = page
    .locator("tr")
    .filter({ hasText: prefix })
    .locator('input[type="checkbox"]:enabled');

  await expect(checkboxes).toHaveCount(expectedCount, { timeout: 30_000 });

  for (let i = 0; i < expectedCount; i += 1) {
    await checkboxes.nth(i).check({ force: true });
  }

  await expect(page.getByTestId("bulk-selected-count")).toContainText(String(expectedCount));
}
