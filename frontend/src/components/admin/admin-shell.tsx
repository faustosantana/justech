"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AdminSidebar } from "@/components/admin/admin-sidebar";
import { LoadingState } from "@/components/brand/loading-state";
import { getAccessToken } from "@/lib/auth";

interface AdminShellProps {
  children: React.ReactNode;
}

/** Shell administrativo — sin sidebar operativo (Command Center, Tareas, etc.). */
export function AdminShell({ children }: AdminShellProps) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getAccessToken()) {
      router.replace("/login");
      return;
    }
    setReady(true);
  }, [router]);

  if (!ready) return <LoadingState message="Verificando sesión…" />;

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden bg-background">
      <header className="shrink-0 border-b border-border bg-card/80 px-4 py-3 backdrop-blur sm:px-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-lg font-semibold tracking-tight">JAIOS — Administración</h1>
            <p className="text-xs text-muted-foreground">Centro de configuración e integraciones</p>
          </div>
          <span className="hidden rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary sm:inline">
            Solo administradores
          </span>
        </div>
      </header>
      <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-auto p-4 sm:p-6 lg:flex-row lg:items-start">
        <AdminSidebar />
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
