"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import { getUserRole } from "@/lib/auth";
import { isLotteryClientRole } from "@/lib/lottery";

const ALLOWED_PREFIXES = ["/lottery", "/login"];

/** Admin lottery paths — lottery_client must never remain here. */
const BLOCKED_PREFIXES = ["/lottery/admin"];

function isAllowedForLotteryClient(pathname: string): boolean {
  if (BLOCKED_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`))) {
    return false;
  }
  return ALLOWED_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

/** Bloquea rutas ajenas para lottery_client en el frontend. */
export function LotteryClientRouteGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const role = typeof window !== "undefined" ? getUserRole() : null;

  useEffect(() => {
    if (!isLotteryClientRole(role)) return;
    if (!isAllowedForLotteryClient(pathname)) {
      router.replace("/lottery");
    }
  }, [pathname, role, router]);

  return <>{children}</>;
}
