"use client";

import { useParams, useSearchParams } from "next/navigation";

import { DGCPInstitutionProfileView } from "@/components/dgcp/dgcp-institution-profile-view";
import { AppShell } from "@/components/layout/app-shell";

export default function InstitutionProfilePage() {
  const { key } = useParams<{ key: string }>();
  const search = useSearchParams();
  const from = search.get("from") || undefined;
  const institutionKey = decodeURIComponent(key || "");

  return (
    <AppShell title="Institución 360°">
      <DGCPInstitutionProfileView institutionKey={institutionKey} backHref={from || undefined} />
    </AppShell>
  );
}
