"use client";

import Link from "next/link";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { HermesAIConfigPanel } from "@/components/settings/hermes-ai-config-panel";
import { Button } from "@/components/ui/button";

export default function ConfiguracionIAHermesPage() {
  return (
    <div>
      <AdminPageHeader
        title="IA — Hermes / Modelos"
        description="DeepSeek V4 Flash vía Huawei ModelArts · System prompts · Diagnóstico del Copiloto"
        action={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link href="/configuracion/ia/prompts">Prompts</Link>
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link href="/configuracion/integraciones">Integraciones</Link>
            </Button>
            <Button variant="outline" size="sm" asChild>
              <Link href="/configuracion/integraciones/diagnostico">Diagnóstico</Link>
            </Button>
          </div>
        }
      />
      <HermesAIConfigPanel />
    </div>
  );
}
