"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { usePlatformAccess } from "@/hooks/use-platform-access";
import { hasPermission } from "@/lib/permissions";

export function DgcpViewGuard({ children }: { children: React.ReactNode }) {
  const { access, loading } = usePlatformAccess();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!access || !hasPermission(access, "view_dgcp")) {
      router.replace("/dashboard");
    }
  }, [access, loading, router]);

  if (loading) {
    return <p className="text-sm text-muted-foreground">Verificando acceso…</p>;
  }
  if (!access || !hasPermission(access, "view_dgcp")) {
    return null;
  }
  return <>{children}</>;
}
