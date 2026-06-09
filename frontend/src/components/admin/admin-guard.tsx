"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { LoadingState } from "@/components/brand/loading-state";
import { apiClient } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import type { AdminAccess } from "@/lib/admin";

export function AdminGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [access, setAccess] = useState<AdminAccess | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getAccessToken()) {
      router.replace("/login");
      return;
    }
    apiClient.getAdminAccess()
      .then((a) => {
        if (!a.can_view) {
          router.replace("/dashboard");
          return;
        }
        setAccess(a);
      })
      .catch(() => router.replace("/dashboard"))
      .finally(() => setLoading(false));
  }, [router]);

  if (loading) {
    return <LoadingState message="Verificando permisos…" />;
  }
  if (!access?.can_view) return null;

  return (
    <div data-admin-mutate={access.can_mutate ? "1" : "0"}>
      {children}
    </div>
  );
}
