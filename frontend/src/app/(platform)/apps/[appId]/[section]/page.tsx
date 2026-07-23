"use client";

import { Suspense, useEffect, useState } from "react";
import { notFound, useParams, useRouter, useSearchParams } from "next/navigation";

import { LoadingState } from "@/components/brand/loading-state";
import { ModuleSectionRenderer } from "@/components/module/module-section-renderer";
import { apiClient } from "@/lib/api";
import type { PlatformAccess } from "@/lib/admin";
import { getModuleSection, MODULE_BY_ID } from "@/lib/modules/registry";

const LOTTERY_SECTION_REDIRECT: Record<string, string> = {
  inicio: "/lottery",
  dashboard: "/lottery",
  consulta: "/lottery/search",
  catalogo: "/lottery/lotteries",
  comparar: "/lottery/compare",
  estadisticas: "/lottery/statistics",
  chat: "/lottery/chat",
  guardadas: "/lottery/saved",
  favoritos: "/lottery/favorites",
  "admin-sync": "/lottery/admin/sync",
  "admin-scheduler": "/lottery/admin/scheduler",
  "admin-lotteries": "/lottery/admin/lotteries",
};

export default function AppModuleSectionPage() {
  return (
    <Suspense fallback={<LoadingState message="Cargando sección…" />}>
      <AppModuleSectionPageInner />
    </Suspense>
  );
}

function AppModuleSectionPageInner() {
  const params = useParams();
  const router = useRouter();
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

  useEffect(() => {
    if (appId !== "lottery") return;
    const target =
      LOTTERY_SECTION_REDIRECT[sectionId] ||
      section?.legacyHref ||
      "/lottery";
    router.replace(target);
  }, [appId, sectionId, section, router]);

  if (!mod) notFound();
  if (appId === "lottery") {
    return <LoadingState message="Abriendo sección de Loterías…" />;
  }
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
