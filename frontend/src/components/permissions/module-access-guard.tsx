"use client";

import Link from "next/link";

import { ModuleEmptyState } from "@/components/module/module-dashboard";
import { usePlatformAccess } from "@/hooks/use-platform-access";
import {
  MODULE_FORBIDDEN_DESCRIPTION,
  MODULE_FORBIDDEN_TITLE,
  canAccessApp,
} from "@/lib/permissions";

/** Bloquea deep links a módulos no permitidos sin chrome de aplicación (sin shell parcial). */
export function ModuleAccessGuard({
  appId,
  children,
}: {
  appId: string;
  children: React.ReactNode;
}) {
  const { access, loading } = usePlatformAccess();

  if (loading) {
    return <p className="p-6 text-sm text-muted-foreground">Verificando acceso…</p>;
  }

  if (!canAccessApp(appId, access)) {
    return (
      <div className="mx-auto flex max-w-lg flex-col gap-4 p-6">
        <ModuleEmptyState title={MODULE_FORBIDDEN_TITLE} description={MODULE_FORBIDDEN_DESCRIPTION} />
        <Link href="/dashboard" className="text-center text-sm text-primary hover:underline">
          Volver al dashboard
        </Link>
      </div>
    );
  }

  return <>{children}</>;
}
