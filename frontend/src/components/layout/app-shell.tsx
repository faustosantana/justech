"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";

import { JaiosAssistant } from "@/components/assistant/jaios-assistant";
import { LoadingState } from "@/components/brand/loading-state";
import { PlatformHeader } from "@/components/layout/platform-header";
import { Sidebar } from "@/components/layout/sidebar";
import { useCompanyContext } from "@/lib/company-context";
import { useAssistantContext } from "@/lib/assistant-context";
import { assistantContextLabel } from "@/lib/assistant-module-label";
import { getAccessToken } from "@/lib/auth";

interface AppShellProps {
  children: React.ReactNode;
  title?: string;
  description?: string;
  hideHeaderTitle?: boolean;
}

export function AppShell({ children, title, description, hideHeaderTitle = false }: AppShellProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const assistant = useAssistantContext();
  const { scopeLabel, context } = useCompanyContext();

  useEffect(() => {
    if (!getAccessToken()) {
      router.replace("/login");
      return;
    }
    setReady(true);
  }, [router]);

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

  return (
    <div className="flex h-full overflow-hidden bg-background">
      <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed((v) => !v)} />
      <div className="platform-backdrop flex min-h-0 min-w-0 flex-1 flex-col">
        <PlatformHeader
          title={hideHeaderTitle ? undefined : title}
          subtitle={hideHeaderTitle ? undefined : description}
        />
        <main className="min-h-0 flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">{children}</main>
      </div>
      {assistantNode}
    </div>
  );
}
