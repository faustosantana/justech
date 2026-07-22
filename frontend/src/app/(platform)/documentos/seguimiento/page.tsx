"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { AppShell } from "@/components/layout/app-shell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import type { DocumentsTrackingSummary } from "@/lib/documents-hub";

export default function DocumentosSeguimientoPage() {
  const [data, setData] = useState<DocumentsTrackingSummary | null>(null);

  useEffect(() => {
    apiClient.getDocumentsHubTracking().then(setData).catch(() => setData(null));
  }, []);

  const metrics = data
    ? [
        { label: "Empresas completas", value: data.companies_complete, href: "/documentos/empresas" },
        { label: "Empresas incompletas", value: data.companies_incomplete, href: "/documentos/empresas" },
        { label: "Documentos vencidos", value: data.documents_expired, href: "/documentos/legales" },
        { label: "Documentos faltantes", value: data.documents_missing, href: "/documentos/pendientes" },
        { label: "Solicitudes enviadas", value: data.requests_sent },
        { label: "Solicitudes pendientes", value: data.requests_pending, href: "/documentos/pendientes" },
        { label: "Solicitudes vencidas", value: data.requests_overdue, href: "/documentos/pendientes" },
      ]
    : [];

  return (
    <AppShell title="Seguimiento documental" description="Resumen ejecutivo de completitud y solicitudes">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {metrics.map((m) => (
          <Card key={m.label}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{m.label}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold">{m.value ?? "—"}</p>
              {m.href && (
                <Link href={m.href} className="text-xs text-primary hover:underline">
                  Ver detalle
                </Link>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </AppShell>
  );
}
