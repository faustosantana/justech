"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  DEFAULT_APPEARANCE,
  loadAppearance,
  resolveBackground,
  saveAppearance,
  type AppearanceSettings,
} from "@/lib/appearance";

type AppearanceContextValue = {
  settings: AppearanceSettings;
  updateSettings: (patch: Partial<AppearanceSettings>) => void;
  resetSettings: () => void;
};

const AppearanceCtx = createContext<AppearanceContextValue | null>(null);

function applyToDocument(settings: AppearanceSettings) {
  const root = document.documentElement;
  root.classList.toggle("dark", settings.mode === "dark");
  root.style.setProperty("--jaios-primary-custom", settings.primaryColor);
  root.style.setProperty("--jaios-secondary-custom", settings.secondaryColor);
  root.style.setProperty("--jaios-glass-blur", `${settings.glassBlur}px`);
  root.style.setProperty("--jaios-glass-opacity", `${settings.glassOpacity / 100}`);
  root.style.setProperty("--jaios-home-bg", resolveBackground(settings));
}

export function AppearanceProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<AppearanceSettings>(DEFAULT_APPEARANCE);

  useEffect(() => {
    const loaded = loadAppearance();
    setSettings(loaded);
    applyToDocument(loaded);
  }, []);

  const updateSettings = useCallback((patch: Partial<AppearanceSettings>) => {
    setSettings((prev) => {
      const next = { ...prev, ...patch };
      saveAppearance(next);
      applyToDocument(next);
      return next;
    });
  }, []);

  const resetSettings = useCallback(() => {
    saveAppearance(DEFAULT_APPEARANCE);
    setSettings(DEFAULT_APPEARANCE);
    applyToDocument(DEFAULT_APPEARANCE);
  }, []);

  const value = useMemo(
    () => ({ settings, updateSettings, resetSettings }),
    [settings, updateSettings, resetSettings],
  );

  return <AppearanceCtx.Provider value={value}>{children}</AppearanceCtx.Provider>;
}

export function useAppearance() {
  const ctx = useContext(AppearanceCtx);
  if (!ctx) throw new Error("useAppearance must be used within AppearanceProvider");
  return ctx;
}
