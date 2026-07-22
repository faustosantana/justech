"use client";

import { Suspense, useEffect, useState } from "react";
import { notFound, useParams, useSearchParams } from "next/navigation";

import { LoadingState } from "@/components/brand/loading-state";
import { ModuleSectionRenderer } from "@/components/module/module-section-renderer";
import { apiClient } from "@/lib/api";
import type { PlatformAccess } from "@/lib/admin";
import { getModuleSection, MODULE_BY_ID } from "@/lib/modules/registry";

export default function AppModuleSectionPage() {
  return (
    <Suspense fallback={<LoadingState message="Cargando sección…" />}>
      <AppModuleSectionPageInner />
    </Suspense>
  );
}

function AppModuleSectionPageInner() {
  const params = useParams();
  const searchParams = useSearchParams();
  const appId = params.appId as string;
  const sectionId = params.section as string;
  const activeView = searchParams.get("view") ?? "list";
  const [access, setAccess] = useState<PlatformAccess | null>(null);

  const mod = MODULE_BY_ID[appId];
  const section = getModuleSection(appId, sectionId);

  useEffect(() => {
    apiClient.getPlatformAccess().then(setAccess).catch(() => setAccess(null));
  }, []);

  if (!mod) notFound();
  if (!section) notFound();

  return (
    <ModuleSectionRenderer
      appId={appId}
      section={section}
      access={access}
      activeView={activeView}
    />
  );
}
