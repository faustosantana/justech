"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { CompanySelector } from "@/components/layout/company-selector";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import type { OdooHealth } from "@/lib/odoo";
import type { M365Health } from "@/lib/m365";

export default function ConfiguracionPage() {
  const [tenantName, setTenantName] = useState("");
  const [odoo, setOdoo] = useState<OdooHealth | null>(null);
  const [m365, setM365] = useState<M365Health | null>(null);
  const [notifyEmail, setNotifyEmail] = useState(true);
  const [notifyTasks, setNotifyTasks] = useState(true);

  useEffect(() => {
    const saved = localStorage.getItem("jaios-prefs");
    if (saved) {
      try {
        const p = JSON.parse(saved);
        setNotifyEmail(p.notifyEmail ?? true);
        setNotifyTasks(p.notifyTasks ?? true);
      } catch {
        /* ignore */
      }
    }
    Promise.allSettled([
      apiClient.getCurrentTenant(),
      apiClient.getOdooHealth(),
      apiClient.getM365Health(),
    ]).then(([t, o, m]) => {
      if (t.status === "fulfilled") setTenantName(t.value.name);
      if (o.status === "fulfilled") setOdoo(o.value);
      if (m.status === "fulfilled") setM365(m.value);
    });
  }, []);

  const savePrefs = () => {
    localStorage.setItem(
      "jaios-prefs",
      JSON.stringify({ notifyEmail, notifyTasks, locale: "es-DO" }),
    );
  };

  return (
    <AppShell title="Configuración" description="Preferencias del tenant y del usuario">
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Empresa activa</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <CompanySelector />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Perfil y tenant</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <p><span className="text-muted-foreground">Tenant activo:</span> {tenantName || "—"}</p>
            <p><span className="text-muted-foreground">Empresa Odoo:</span> {odoo?.active_company_name || "No conectado"}</p>
            <p><span className="text-muted-foreground">Idioma:</span> Español (República Dominicana)</p>
            <Button variant="outline" size="sm" asChild className="mt-2">
              <Link href="/odoo/settings">Configuración Odoo</Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Integraciones</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex items-center justify-between rounded-lg border border-border p-3">
              <div>
                <p className="font-medium">Odoo</p>
                <p className="text-muted-foreground">{odoo?.connected ? "Conectado" : "No conectado"}</p>
              </div>
              <Button variant="outline" size="sm" asChild>
                <Link href="/odoo/settings">Gestionar</Link>
              </Button>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-border p-3">
              <div>
                <p className="font-medium">Microsoft 365</p>
                <p className="text-muted-foreground">{m365?.connected ? "Conectado" : m365?.message || "No conectado"}</p>
              </div>
              <Button variant="outline" size="sm" asChild>
                <Link href="/m365">Ver estado</Link>
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Notificaciones</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={notifyEmail} onChange={(e) => setNotifyEmail(e.target.checked)} />
              Alertas por correo (cuando esté disponible)
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={notifyTasks} onChange={(e) => setNotifyTasks(e.target.checked)} />
              Recordatorios de tareas vencidas
            </label>
            <Button size="sm" onClick={savePrefs}>Guardar preferencias</Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Administración</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm text-muted-foreground">
              Usuarios, roles, módulos y reglas de asignación se gestionan en el Centro de Administración.
            </p>
            <Button variant="outline" size="sm" asChild>
              <Link href="/admin">Abrir administración</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
