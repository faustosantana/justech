"use client";

import { Suspense, useEffect } from "react";
import { notFound, useParams } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { LoadingState } from "@/components/brand/loading-state";
import { DgcpViewGuard } from "@/components/permissions/dgcp-view-guard";
import { setCurrentAppId } from "@/lib/app-navigation";
import { MODULE_BY_ID } from "@/lib/modules/registry";

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

  useEffect(() => {
    if (mod) setCurrentAppId(appId);
  }, [appId, mod]);

  if (!mod) notFound();

  const content =
    mod.id === "licitaciones" ? (
      <DgcpViewGuard>{children}</DgcpViewGuard>
    ) : (
      children
    );

  return (
    <AppShell hideHeaderTitle>
      {content}
    </AppShell>
  );
}
