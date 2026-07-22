"use client";

import { Suspense } from "react";

import { ModuleEmptyState, ModuleSectionHeader, ModuleViewSwitcher } from "@/components/module/module-dashboard";
import { PermissionGate } from "@/components/module/permission-gate";
import { LoadingState } from "@/components/brand/loading-state";
import { renderSectionContent } from "@/lib/modules/render-section-content";
import type { PlatformAccess } from "@/lib/admin";
import type { ModuleSection } from "@/lib/modules/types";

const VIEW_LABELS: Record<string, string> = {
  dashboard: "Dashboard",
  list: "Lista",
  kanban: "Kanban",
  calendar: "Calendario",
  charts: "Gráficos",
  reports: "Reportes",
  config: "Configuración",
};

type Props = {
  appId: string;
  section: ModuleSection;
  access: PlatformAccess | null;
  activeView?: string;
};

export function ModuleSectionRenderer({ appId, section, access, activeView = "list" }: Props) {
  const views = section.views?.map((v) => ({ id: v, label: VIEW_LABELS[v] ?? v })) ?? [{ id: "list", label: "Lista" }];

  return (
    <PermissionGate
      roles={section.roles}
      moduleKey={section.moduleKey}
      access={access}
      fallback={<ModuleEmptyState title="Sin permiso" description="No tienes acceso a esta sección." />}
    >
      <ModuleSectionHeader title={section.label} description={section.description}>
        {views.length > 1 && (
          <ModuleViewSwitcher appId={appId} sectionId={section.id} active={activeView} views={views} />
        )}
      </ModuleSectionHeader>
      <Suspense fallback={<LoadingState message="Cargando…" />}>
        {renderSectionContent(section, appId, activeView)}
      </Suspense>
    </PermissionGate>
  );
}
