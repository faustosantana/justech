"use client";

import { useParams, useSearchParams } from "next/navigation";

import { DGCPSupplierProfileView } from "@/components/dgcp/dgcp-supplier-profile-view";
import { AppShell } from "@/components/layout/app-shell";

export default function SupplierProfilePage() {
  const { key } = useParams<{ key: string }>();
  const search = useSearchParams();
  const from = search.get("from") || undefined;
  const supplierKey = decodeURIComponent(key || "");

  return (
    <AppShell title="Proveedor 360°">
      <DGCPSupplierProfileView supplierKey={supplierKey} backHref={from || undefined} />
    </AppShell>
  );
}
