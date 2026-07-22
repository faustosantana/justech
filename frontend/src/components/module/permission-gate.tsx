"use client";

import type { ReactNode } from "react";

import type { PlatformAccess } from "@/lib/admin";
import { getUserRole } from "@/lib/auth";

type Props = {
  roles?: string[];
  moduleKey?: string;
  access: PlatformAccess | null;
  children: ReactNode;
  fallback?: ReactNode;
};

export function PermissionGate({ roles, moduleKey, access, children, fallback = null }: Props) {
  if (roles?.length) {
    const role = (getUserRole() ?? access?.role ?? "").toLowerCase();
    if (!roles.some((r) => role.includes(r))) return fallback;
  }
  if (moduleKey && access?.modules && access.modules[moduleKey] === false) {
    return fallback;
  }
  return children;
}
