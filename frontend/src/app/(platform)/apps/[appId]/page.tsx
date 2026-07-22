"use client";

import { notFound, useParams } from "next/navigation";

import { ModuleDashboardPage } from "@/components/module/module-dashboard-page";
import { MODULE_BY_ID } from "@/lib/modules/registry";

export default function AppModuleDashboardPage() {
  const params = useParams();
  const appId = params.appId as string;

  if (!MODULE_BY_ID[appId]) notFound();

  return <ModuleDashboardPage appId={appId} />;
}
