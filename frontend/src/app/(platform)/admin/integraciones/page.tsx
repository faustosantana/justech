"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { AdminNav } from "@/components/admin/admin-nav";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import type { TenantSettings } from "@/lib/admin";

export default function AdminIntegracionesPage() {
  const [settings, setSettings] = useState<TenantSettings | null>(null);

  useEffect(() => {
    apiClient.getAdminSettings().then(setSettings);
  }, []);

  if (!settings) {
    return (
      <AppShell title="Integraciones">
        <p className="text-sm text-muted-foreground">Cargando…</p>
      </AppShell>
    );
  }

  return (
    <AppShell title="Integraciones y configuración" description="Estado de integraciones y políticas del tenant">
      <AdminNav />
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle className="text-base">Configuración general</CardTitle></CardHeader>
          <CardContent className="text-sm space-y-2">
            <p><span className="text-muted-foreground">Idioma:</span> Español RD ({settings.language})</p>
            <p><span className="text-muted-foreground">Zona horaria:</span> {settings.timezone}</p>
            <p><span className="text-muted-foreground">Moneda:</span> {settings.default_currency}</p>
            <p><span className="text-muted-foreground">Empresa principal:</span> {settings.primary_company ?? "Justech Demo"}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="text-base">Estado de integraciones</CardTitle></CardHeader>
          <CardContent className="text-sm space-y-2">
            {Object.entries(settings.integration_status).map(([k, v]) => (
              <p key={k}><span className="text-muted-foreground capitalize">{k}:</span> {v}</p>
            ))}
          </CardContent>
        </Card>
        {settings.qa_policies_visible && (
          <Card className="md:col-span-2">
            <CardHeader><CardTitle className="text-base">Políticas de QA</CardTitle></CardHeader>
            <CardContent className="text-sm text-muted-foreground space-y-1">
              <p>· Ejecutar <code className="text-xs">make qa-self-heal</code> antes de cerrar fases</p>
              <p>· No usar <code className="text-xs">npm run build</code> con next dev activo</p>
              <p>· Build seguro: stop frontend → run --rm build → up</p>
            </CardContent>
          </Card>
        )}
      </div>
    </AppShell>
  );
}
