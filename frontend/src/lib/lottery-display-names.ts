/**
 * UI-only display names with correct Spanish accents.
 * Does not change UUIDs, slugs, or database records.
 */

const BY_ID: Record<string, string> = {
  "0118037f-8f8b-4a82-899c-42cd50b6e194": "Lotería Nacional",
  "523875dc-c7f4-4883-b0f6-b440397e3aeb": "Quiniela Leidsa",
  "b9f2c5a2-bc3e-4382-9b6d-3cee16db00fd": "Quiniela Loteka",
  "43250709-ee65-476f-91f6-cb8438f49d65": "Gana Más",
  "205c58d2-cfcf-44e6-894d-97358b3d540b": "Quiniela Real",
  "1c488641-adb6-4790-89e7-879d361da7cc": "New York 2:30",
  "1624b6f2-88c6-42b5-a597-bf9c0f98a6b5": "New York 10:30",
};

const BY_RAW: Record<string, string> = {
  "Loteria Nacional": "Lotería Nacional",
  "Gana Mas": "Gana Más",
};

export function lotteryDisplayName(
  idOrName: string | null | undefined,
  fallback?: string | null,
): string {
  if (!idOrName && !fallback) return "—";
  const id = String(idOrName || "").trim();
  if (BY_ID[id]) return BY_ID[id];
  const raw = String(fallback || idOrName || "").trim();
  return BY_RAW[raw] || raw || "—";
}
