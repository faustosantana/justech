"use client";

import Link from "next/link";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { HermesPromptsAdminPanel } from "@/components/settings/hermes-prompts-admin-panel";
import { Button } from "@/components/ui/button";

export default function ConfiguracionIAPromptsPage() {
  return (
    <div>
      <AdminPageHeader
        title="IA — Prompts Hermes"
        description="System prompts por módulo, rol, usuario y herramienta · Jerarquía con seguridad obligatoria"
        action={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link href="/configuracion/ia/hermes">Modelos / Diagnóstico</Link>
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link href="/configuracion/seguridad/permisos-ia">Permisos IA</Link>
            </Button>
          </div>
        }
      />
      <HermesPromptsAdminPanel />
    </div>
  );
}
