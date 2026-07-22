"use client";

import { RotateCcw, Upload } from "lucide-react";
import { useRef } from "react";

import { Button } from "@/components/ui/button";
import { BACKGROUND_PRESETS, type ThemeMode, type DensityMode } from "@/lib/appearance";
import { useAppearance } from "@/lib/appearance-context";
import { cn } from "@/lib/utils";

const PRIMARY_PRESETS = ["#2563EB", "#0EA5E9", "#8B5CF6", "#10B981", "#F59E0B", "#EF4444"];

export function AppearanceSettings() {
  const { settings, updateSettings, resetSettings } = useAppearance();
  const fileRef = useRef<HTMLInputElement>(null);

  function onImageUpload(file: File | undefined) {
    if (!file || file.size > 2_500_000) return;
    const reader = new FileReader();
    reader.onload = () => {
      updateSettings({ customBackgroundUrl: String(reader.result), backgroundPreset: "custom" });
    };
    reader.readAsDataURL(file);
  }

  return (
    <div className="space-y-8">
      <section className="brand-surface p-6">
        <h2 className="text-lg font-semibold">Fondo</h2>
        <p className="mt-1 text-sm text-muted-foreground">Predeterminados o imagen personalizada.</p>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {BACKGROUND_PRESETS.map((preset) => (
            <button
              key={preset.id}
              type="button"
              onClick={() => updateSettings({ backgroundPreset: preset.id, customBackgroundUrl: null })}
              className={cn(
                "overflow-hidden rounded-xl border-2 p-1 transition",
                settings.backgroundPreset === preset.id && !settings.customBackgroundUrl
                  ? "border-primary"
                  : "border-transparent hover:border-border",
              )}
            >
              <div className="h-16 rounded-lg" style={{ background: preset.light }} />
              <p className="mt-1 text-xs font-medium">{preset.label}</p>
            </button>
          ))}
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => onImageUpload(e.target.files?.[0])}
          />
          <Button type="button" variant="outline" size="sm" onClick={() => fileRef.current?.click()}>
            <Upload className="mr-2 h-4 w-4" />
            Subir imagen
          </Button>
          {settings.customBackgroundUrl && (
            <Button type="button" variant="ghost" size="sm" onClick={() => updateSettings({ customBackgroundUrl: null })}>
              Quitar imagen
            </Button>
          )}
        </div>
      </section>

      <section className="brand-surface p-6">
        <h2 className="text-lg font-semibold">Colores</h2>
        <div className="mt-4 flex flex-wrap gap-2">
          {PRIMARY_PRESETS.map((color) => (
            <button
              key={color}
              type="button"
              onClick={() => updateSettings({ primaryColor: color })}
              className={cn(
                "h-9 w-9 rounded-full border-2 transition hover:scale-110",
                settings.primaryColor === color ? "border-foreground" : "border-transparent",
              )}
              style={{ backgroundColor: color }}
              aria-label={`Color ${color}`}
            />
          ))}
        </div>
      </section>

      <section className="brand-surface grid gap-6 p-6 md:grid-cols-2">
        <div>
          <h2 className="text-lg font-semibold">Modo</h2>
          <div className="mt-3 flex gap-2">
            {(["light", "dark"] as ThemeMode[]).map((mode) => (
              <Button
                key={mode}
                type="button"
                variant={settings.mode === mode ? "default" : "outline"}
                size="sm"
                onClick={() => updateSettings({ mode })}
              >
                {mode === "light" ? "Claro" : "Oscuro"}
              </Button>
            ))}
          </div>
        </div>
        <div>
          <h2 className="text-lg font-semibold">Densidad</h2>
          <div className="mt-3 flex gap-2">
            {(["comfortable", "compact"] as DensityMode[]).map((d) => (
              <Button
                key={d}
                type="button"
                variant={settings.density === d ? "default" : "outline"}
                size="sm"
                onClick={() => updateSettings({ density: d })}
              >
                {d === "comfortable" ? "Cómodo" : "Compacto"}
              </Button>
            ))}
          </div>
        </div>
      </section>

      <section className="brand-surface p-6">
        <h2 className="text-lg font-semibold">Efectos</h2>
        <div className="mt-4 space-y-4">
          <label className="block text-sm">
            <span className="text-muted-foreground">Transparencia vidrio ({settings.glassOpacity}%)</span>
            <input
              type="range"
              min={40}
              max={95}
              value={settings.glassOpacity}
              onChange={(e) => updateSettings({ glassOpacity: Number(e.target.value) })}
              className="mt-2 w-full"
            />
          </label>
          <label className="block text-sm">
            <span className="text-muted-foreground">Blur ({settings.glassBlur}px)</span>
            <input
              type="range"
              min={0}
              max={24}
              value={settings.glassBlur}
              onChange={(e) => updateSettings({ glassBlur: Number(e.target.value) })}
              className="mt-2 w-full"
            />
          </label>
        </div>
      </section>

      <Button type="button" variant="outline" onClick={resetSettings}>
        <RotateCcw className="mr-2 h-4 w-4" />
        Restaurar predeterminados
      </Button>
    </div>
  );
}
