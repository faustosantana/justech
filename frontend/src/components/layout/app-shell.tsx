"use client";

import { Suspense, useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { JaiosAssistant } from "@/components/assistant/jaios-assistant";
import { LoadingState } from "@/components/brand/loading-state";
import { ApplicationSidebar } from "@/components/navigation/application-sidebar";
import { ApplicationTopbar } from "@/components/navigation/application-topbar";
import { PlatformHeader } from "@/components/layout/platform-header";
import { apiClient } from "@/lib/api";
import type { PlatformAccess } from "@/lib/admin";
import { resolveActiveApp } from "@/lib/app-navigation";
import { useCompanyContext } from "@/lib/company-context";
import { useAssistantContext } from "@/lib/assistant-context";
import { assistantContextLabel } from "@/lib/assistant-module-label";
import { getAccessToken } from "@/lib/auth";
import { LotteryClientRouteGuard } from "@/components/lottery/lottery-client-route-guard";
import { cn } from "@/lib/utils";

export interface AppShellProps {
  children: React.ReactNode;
  title?: string;
  description?: string;
  hideHeaderTitle?: boolean;
  /** Pantalla de aplicaciones — sin menú contextual */
  variant?: "default" | "launcher";
  hideHeaderSearch?: boolean;
}

function AppShellInner({
  children,
  title,
  description,
  hideHeaderTitle = false,
  variant = "default",
  hideHeaderSearch = false,
}: AppShellProps) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const search = searchParams.toString() ? `?${searchParams.toString()}` : "";
  const [ready, setReady] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [access, setAccess] = useState<PlatformAccess | null>(null);
  const assistant = useAssistantContext();
  const { scopeLabel, context } = useCompanyContext();

  const isLauncher = variant === "launcher" || pathname === "/dashboard";
  const activeApp = isLauncher ? null : resolveActiveApp(pathname, search);
  const useApplicationChrome = Boolean(activeApp) && !pathname.startsWith("/configuracion");

  useEffect(() => {
    if (!getAccessToken()) {
      router.replace("/login");
      return;
    }
    setReady(true);
    apiClient.getPlatformAccess().then(setAccess).catch(() => setAccess(null));
  }, [router]);

  // ≤768: start collapsed so the AppShell drawer is the only navigation surface.
  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mq = window.matchMedia("(max-width: 768px)");
    const apply = () => {
      if (mq.matches) setSidebarCollapsed(true);
    };
    apply();
    mq.addEventListener?.("change", apply);
    return () => mq.removeEventListener?.("change", apply);
  }, []);

  useEffect(() => {
    const isRecordDetailRoute =
      /\/dgcp\/[^/]+/.test(pathname) ||
      /\/odoo\/(customers|invoices|products|vendors)\/[^/]+/.test(pathname);
    if (!isRecordDetailRoute) {
      assistant.clearRecordContext();
    }
  }, [pathname, assistant.clearRecordContext]);

  const moduleContextLabel = assistantContextLabel(pathname, assistant.recordType, assistant.recordId);
  const companyScopeLabel = scopeLabel || "Sin empresa seleccionada";

  const assistantNode = (
    <JaiosAssistant
      companyContextId={context?.active_company_id ?? null}
      recordType={assistant.recordType}
      recordId={assistant.recordId}
      presetQuestion={assistant.presetQuestion}
      contextLabel={moduleContextLabel}
      companyScopeLabel={companyScopeLabel}
      onClearRecordContext={assistant.clearRecordContext}
      controlledOpen={assistant.copilotOpen}
      onOpenChange={(open) => (open ? assistant.openCopilot() : assistant.closeCopilot())}
      proactiveBriefing={assistant.proactiveMessage}
    />
  );

  if (!ready) {
    return (
      <>
        <LoadingState message="Verificando sesión…" />
        {assistantNode}
      </>
    );
  }

  if (isLauncher) {
    return (
      <LotteryClientRouteGuard>
        <div className="flex h-full flex-col overflow-hidden bg-background">
          <PlatformHeader hideSearch />
          <main className="min-h-0 flex-1 overflow-y-auto">{children}</main>
          {assistantNode}
        </div>
      </LotteryClientRouteGuard>
    );
  }

  if (useApplicationChrome && activeApp) {
    return (
      <LotteryClientRouteGuard>
        <div className="flex h-full overflow-hidden bg-background">
          <ApplicationSidebar
            app={activeApp}
            collapsed={sidebarCollapsed}
            onToggle={() => setSidebarCollapsed((v) => !v)}
            access={access}
          />
          <div className="flex min-h-0 min-w-0 flex-1 flex-col">
            <ApplicationTopbar app={activeApp} pathname={pathname} search={search} />
            <main className="min-h-0 flex-1 overflow-y-auto p-4 md:p-6">{children}</main>
          </div>
          {assistantNode}
        </div>
      </LotteryClientRouteGuard>
    );
  }

  return (
    <LotteryClientRouteGuard>
      <div className="flex h-full flex-col overflow-hidden bg-background">
        <PlatformHeader
          title={hideHeaderTitle ? undefined : title}
          subtitle={hideHeaderTitle ? undefined : description}
          hideSearch={hideHeaderSearch}
        />
        <main className={cn("min-h-0 flex-1 overflow-y-auto p-4 md:p-6 lg:p-8")}>{children}</main>
        {assistantNode}
      </div>
    </LotteryClientRouteGuard>
  );
}

export function AppShell(props: AppShellProps) {
  return (
    <Suspense fallback={<LoadingState message="Cargando…" />}>
      <AppShellInner {...props} />
    </Suspense>
  );
}
