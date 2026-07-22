"use client";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { AppearanceSettings } from "@/components/settings/appearance-settings";

export default function AparienciaPage() {
  return (
    <div className="space-y-6">
      <AdminPageHeader
        title="Apariencia"
        description="Personaliza el fondo, colores y densidad de tu experiencia JAIOS. Los cambios se guardan en este dispositivo."
      />
      <AppearanceSettings />
    </div>
  );
}
