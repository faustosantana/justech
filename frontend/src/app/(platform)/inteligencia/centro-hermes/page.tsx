"use client";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { HermesIntelligenceCenterSection } from "@/components/modules/agentes-ia/hermes-intelligence-center";
import { AppShell } from "@/components/layout/app-shell";

export default function CentroHermesPage() {
  return (
    <AppShell hideHeaderTitle>
      <AdminPageHeader
        title="Centro de Inteligencia Hermes"
        description="Oportunidades, alertas y acciones sugeridas · Solo recomendaciones con fuente"
      />
      <HermesIntelligenceCenterSection />
    </AppShell>
  );
}
