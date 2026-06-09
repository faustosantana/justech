"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { OpportunitiesTable } from "@/components/dgcp/opportunities-table";
import { AppShell } from "@/components/layout/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import type { DGCPOpportunity } from "@/lib/dgcp";

export default function OportunidadesPage() {
  const router = useRouter();
  const [items, setItems] = useState<DGCPOpportunity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient
      .getDGCPOpportunities()
      .then((data) => setItems(data.items))
      .catch(() => router.replace("/login"))
      .finally(() => setLoading(false));
  }, [router]);

  return (
    <AppShell title="Expedientes DGCP" description="Listado completo de licitaciones y procesos DGCP">
      <Card>
        <CardHeader>
          <CardTitle>{items.length} oportunidades registradas</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-muted-foreground">Cargando…</p>
          ) : (
            <OpportunitiesTable items={items} detailPath={(id) => `/dgcp/${id}`} />
          )}
        </CardContent>
      </Card>
    </AppShell>
  );
}
