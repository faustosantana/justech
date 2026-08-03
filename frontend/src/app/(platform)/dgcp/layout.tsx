"use client";

import Link from "next/link";

import { AppShell } from "@/components/layout/app-shell";
import { LoadingState } from "@/components/brand/loading-state";
import { ModuleEmptyState } from "@/components/module/module-dashboard";
import { usePlatformAccess } from "@/hooks/use-platform-access";
import {
  MODULE_FORBIDDEN_DESCRIPTION,
  MODULE_FORBIDDEN_TITLE,
  canAccessApp,
} from "@/lib/permissions";

export default function DgcpLayout({ children }: { children: React.ReactNode }) {
  const { access, loading } = usePlatformAccess();

  if (loading) {
    return <LoadingState message="Verificando acceso…" />;
  }

  if (!canAccessApp("licitaciones", access)) {
    return (
      <AppShell variant="launcher" hideHeaderSearch>
        <div className="mx-auto flex max-w-lg flex-col gap-4 p-6">
          <ModuleEmptyState title={MODULE_FORBIDDEN_TITLE} description={MODULE_FORBIDDEN_DESCRIPTION} />
          <Link href="/dashboard" className="text-center text-sm text-primary hover:underline">
            Volver al dashboard
          </Link>
        </div>
      </AppShell>
    );
  }

  return <>{children}</>;
}
