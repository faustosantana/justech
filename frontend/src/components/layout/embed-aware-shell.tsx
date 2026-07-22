"use client";

import { Suspense, type ReactNode } from "react";
import { useSearchParams } from "next/navigation";

import { AppShell, type AppShellProps } from "@/components/layout/app-shell";

function EmbedAwareShellInner({ children, ...props }: AppShellProps) {
  const searchParams = useSearchParams();
  if (searchParams.get("embed") === "1") {
    return <div className="min-h-0 bg-background p-2 md:p-4">{children}</div>;
  }
  return <AppShell {...props}>{children}</AppShell>;
}

export function EmbedAwareShell(props: AppShellProps) {
  return (
    <Suspense fallback={<AppShell {...props}>{props.children}</AppShell>}>
      <EmbedAwareShellInner {...props} />
    </Suspense>
  );
}

export function EmbedOnly({ children }: { children: ReactNode }) {
  const searchParams = useSearchParams();
  if (searchParams.get("embed") !== "1") return null;
  return children;
}
