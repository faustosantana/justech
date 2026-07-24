"use client";

import { useEffect } from "react";
import { notFound, useParams, useRouter } from "next/navigation";

import { LoadingState } from "@/components/brand/loading-state";
import { ModuleDashboardPage } from "@/components/module/module-dashboard-page";
import { MODULE_BY_ID } from "@/lib/modules/registry";

/** Lottery lives on App Router /lottery — redirect away from broken /apps/lottery. */
export default function AppModuleDashboardPage() {
  const params = useParams();
  const router = useRouter();
  const appId = params.appId as string;
  const mod = MODULE_BY_ID[appId];

  useEffect(() => {
    if (appId === "lottery") {
      router.replace("/lottery");
    }
  }, [appId, router]);

  if (!mod) notFound();
  if (appId === "lottery") {
    return <LoadingState message="Abriendo Lottery IA Control Center…" />;
  }

  return <ModuleDashboardPage appId={appId} />;
}
