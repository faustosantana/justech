import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

const ROOT = path.resolve(__dirname, "..");
const E2E_DIR = process.env.E2E_DIR ?? path.join(ROOT, ".qa/e2e");

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  timeout: 180_000,
  expect: { timeout: 30_000 },
  globalSetup: path.join(__dirname, "global-setup.ts"),
  reporter: [
    ["list"],
    ["json", { outputFile: path.join(E2E_DIR, "results.json") }],
    ["html", { outputFolder: path.join(E2E_DIR, "html-report"), open: "never" }],
  ],
  outputDir: path.join(E2E_DIR, "test-results"),
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "on",
    video: "off",
    storageState: path.join(E2E_DIR, "auth-state.json"),
  },
  projects: [
    {
      name: "chrome",
      use: {
        ...devices["Desktop Chrome"],
        channel: "chrome",
      },
    },
  ],
});
