"use client";

import Link from "next/link";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { CopilotPermissionsPanel } from "@/components/settings/copilot-permissions-panel";
import { Button } from "@/components/ui/button";

export default function PermisosIAPage() {
  return (
    <div>
      <AdminPageHeader
        title="Seguridad — Permisos IA"
        description="Control de acceso del Copiloto · Roles, scopes, clientes asignados y auditoría"
        action={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link href="/configuracion/ia/prompts">Prompts Hermes</Link>
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link href="/configuracion/seguridad">Seguridad general</Link>
            </Button>
          </div>
        }
      />
      <CopilotPermissionsPanel />
    </div>
  );
}
