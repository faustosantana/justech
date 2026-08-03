"use client";

import { Suspense, useEffect } from "react";
import { notFound, useParams } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { LoadingState } from "@/components/brand/loading-state";
import { DgcpViewGuard } from "@/components/permissions/dgcp-view-guard";
import { ModuleAccessGuard } from "@/components/permissions/module-access-guard";
import { usePlatformAccess } from "@/hooks/use-platform-access";
import { setCurrentAppId } from "@/lib/app-navigation";
import { MODULE_BY_ID } from "@/lib/modules/registry";
import { canAccessApp } from "@/lib/permissions";

export default function AppModuleLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<LoadingState message="Cargando aplicación…" />}>
      <AppModuleLayoutInner>{children}</AppModuleLayoutInner>
    </Suspense>
  );
}

function AppModuleLayoutInner({ children }: { children: React.ReactNode }) {
  const params = useParams();
  const appId = params.appId as string;
  const mod = MODULE_BY_ID[appId];
  const { access, loading } = usePlatformAccess();
  const allowed = !loading && canAccessApp(appId, access);

  useEffect(() => {
    if (mod && allowed) setCurrentAppId(appId);
  }, [appId, mod, allowed]);

  if (!mod) notFound();

  // Denied: launcher chrome only (no ApplicationSidebar of the forbidden module).
  if (!loading && !canAccessApp(appId, access)) {
    return (
      <AppShell variant="launcher" hideHeaderSearch>
        <ModuleAccessGuard appId={appId}>{null}</ModuleAccessGuard>
      </AppShell>
    );
  }

  const content =
    mod.id === "licitaciones" ? (
      <DgcpViewGuard>
        <ModuleAccessGuard appId={appId}>{children}</ModuleAccessGuard>
      </DgcpViewGuard>
    ) : (
      <ModuleAccessGuard appId={appId}>{children}</ModuleAccessGuard>
    );

  return (
    <AppShell hideHeaderTitle>
      {loading ? <LoadingState message="Verificando acceso…" /> : content}
    </AppShell>
  );
}
