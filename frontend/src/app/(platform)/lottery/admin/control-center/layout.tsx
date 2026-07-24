"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { getAccessToken, getUserRole } from "@/lib/auth";
import { canAccessLotteryModule } from "@/lib/lottery";

/**
 * J-10X: Control Center routes use the single AppShell sidebar only.
 * Nested “Inteligencia / Metodología” nav removed — product identity is Lottery IA.
 */
export default function ControlCenterLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getAccessToken()) {
      router.replace("/login?session=expired");
      return;
    }
    if (!canAccessLotteryModule(getUserRole())) {
      router.replace("/");
      return;
    }
    setReady(true);
  }, [router]);

  if (!ready) {
    return (
      <AppShell>
        <div className="p-6 text-sm text-muted-foreground">Verificando acceso…</div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-7xl p-4 min-[769px]:p-6">{children}</div>
    </AppShell>
  );
}
