import { getAccessToken, getTenantId } from "@/lib/auth";

export type ThemeMode = "light" | "dark";
export type DensityMode = "comfortable" | "compact";

export type AppearanceSettings = {
  backgroundPreset: string;
  customBackgroundUrl?: string | null;
  primaryColor: string;
  secondaryColor: string;
  mode: ThemeMode;
  glassBlur: number;
  glassOpacity: number;
  density: DensityMode;
};

export const DEFAULT_APPEARANCE: AppearanceSettings = {
  backgroundPreset: "aurora",
  customBackgroundUrl: null,
  primaryColor: "#2563EB",
  secondaryColor: "#64748B",
  mode: "light",
  glassBlur: 12,
  glassOpacity: 72,
  density: "comfortable",
};

export const BACKGROUND_PRESETS: {
  id: string;
  label: string;
  light: string;
  dark: string;
}[] = [
  {
    id: "aurora",
    label: "Aurora",
    light: "radial-gradient(ellipse 80% 50% at 20% -10%, rgba(37,99,235,0.12), transparent 50%), radial-gradient(ellipse 60% 40% at 90% 100%, rgba(99,102,241,0.08), transparent 50%), linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%)",
    dark: "radial-gradient(ellipse 80% 50% at 20% -10%, rgba(37,99,235,0.2), transparent 50%), radial-gradient(ellipse 60% 40% at 90% 100%, rgba(99,102,241,0.15), transparent 50%), linear-gradient(180deg, #0f172a 0%, #1e293b 100%)",
  },
  {
    id: "ocean",
    label: "Océano",
    light: "linear-gradient(135deg, #e0f2fe 0%, #f0f9ff 50%, #f8fafc 100%)",
    dark: "linear-gradient(135deg, #0c4a6e 0%, #0f172a 50%, #020617 100%)",
  },
  {
    id: "slate",
    label: "Pizarra",
    light: "linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%)",
    dark: "linear-gradient(180deg, #1e293b 0%, #0f172a 100%)",
  },
  {
    id: "violet",
    label: "Violeta",
    light: "radial-gradient(ellipse at top, rgba(139,92,246,0.1), transparent 60%), linear-gradient(180deg, #faf5ff 0%, #f5f3ff 100%)",
    dark: "radial-gradient(ellipse at top, rgba(139,92,246,0.2), transparent 60%), linear-gradient(180deg, #1e1b4b 0%, #0f172a 100%)",
  },
  {
    id: "mint",
    label: "Menta",
    light: "linear-gradient(135deg, #ecfdf5 0%, #f0fdf4 50%, #f8fafc 100%)",
    dark: "linear-gradient(135deg, #064e3b 0%, #0f172a 100%)",
  },
  {
    id: "corporate",
    label: "Corporativo",
    light: "linear-gradient(180deg, #ffffff 0%, #f1f5f9 100%)",
    dark: "linear-gradient(180deg, #1e293b 0%, #334155 100%)",
  },
];

function storageKey(): string {
  const tenant = getTenantId() ?? "default";
  let user = "user";
  const token = getAccessToken();
  if (token) {
    try {
      const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
      user = payload.sub ?? payload.user_id ?? payload.email ?? user;
    } catch {
      /* ignore */
    }
  }
  return `jaios-appearance:${tenant}:${user}`;
}

export function loadAppearance(): AppearanceSettings {
  if (typeof window === "undefined") return DEFAULT_APPEARANCE;
  try {
    const raw = localStorage.getItem(storageKey());
    if (!raw) return DEFAULT_APPEARANCE;
    return { ...DEFAULT_APPEARANCE, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_APPEARANCE;
  }
}

export function saveAppearance(settings: AppearanceSettings): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(storageKey(), JSON.stringify(settings));
}

export function resolveBackground(settings: AppearanceSettings): string {
  if (settings.customBackgroundUrl) {
    return `url(${settings.customBackgroundUrl}) center/cover no-repeat`;
  }
  const preset = BACKGROUND_PRESETS.find((p) => p.id === settings.backgroundPreset) ?? BACKGROUND_PRESETS[0];
  return settings.mode === "dark" ? preset.dark : preset.light;
}
