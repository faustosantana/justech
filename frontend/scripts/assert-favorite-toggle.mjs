#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const launcher = fs.readFileSync(path.join(root, "src/components/navigation/apps-launcher.tsx"), "utf8");
const ftPath = path.join(root, "src/components/navigation/favorite-toggle.tsx");
if (!fs.existsSync(ftPath)) {
  console.error("FAIL: favorite-toggle.tsx missing");
  process.exit(1);
}
const ft = fs.readFileSync(ftPath, "utf8");
if (!/export function FavoriteToggle\b/.test(ft)) {
  console.error("FAIL: FavoriteToggle not exported from favorite-toggle.tsx");
  process.exit(1);
}
if (!launcher.includes("@/components/navigation/favorite-toggle")) {
  console.error("FAIL: apps-launcher must import FavoriteToggle from favorite-toggle");
  process.exit(1);
}
if (launcher.includes('FavoriteToggle } from "@/components/navigation/application-sidebar"')) {
  console.error("FAIL: apps-launcher still imports FavoriteToggle from application-sidebar");
  process.exit(1);
}
if (!/<FavoriteToggle[\s>]/.test(launcher)) {
  console.error("FAIL: AppsLauncher does not render FavoriteToggle");
  process.exit(1);
}
console.log("PASS: FavoriteToggle module wired; not undefined by import path");
