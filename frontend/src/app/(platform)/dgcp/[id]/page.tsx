"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { OpportunityDetail } from "@/components/dgcp/opportunity-detail";
import { AppShell } from "@/components/layout/app-shell";
import { apiClient } from "@/lib/api";
import type { DGCPOpportunity } from "@/lib/dgcp";

export default function OpportunityDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [opportunity, setOpportunity] = useState<DGCPOpportunity | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    apiClient
      .getDGCPOpportunity(id)
      .then(setOpportunity)
      .catch(() => router.replace("/dgcp"))
      .finally(() => setLoading(false));
  }, [id, router]);

  return (
    <AppShell title="Detalle de oportunidad">
      {loading ? (
        <p className="text-muted-foreground">Cargando…</p>
      ) : opportunity ? (
        <OpportunityDetail opportunity={opportunity} />
      ) : null}
    </AppShell>
  );
}
