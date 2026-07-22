"use client";

import { IntegrationForm } from "@/components/settings/integration-form";
import { AppearanceSettings } from "@/components/settings/appearance-settings";
import { CopilotPermissionsPanel } from "@/components/settings/copilot-permissions-panel";
import { HermesAIConfigPanel } from "@/components/settings/hermes-ai-config-panel";
import { HermesPromptsAdminPanel } from "@/components/settings/hermes-prompts-admin-panel";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";

type ConfigKey =
  | "general"
  | "integraciones"
  | "odoo"
  | "whatsapp"
  | "m365"
  | "dgcp"
  | "ia"
  | "prompts"
  | "apariencia"
  | "permisos"
  | "seguridad"
  | "auditoria"
  | "empresas"
  | "usuarios";

export function ModuleConfigEmbed({ configKey }: { configKey: ConfigKey }) {
  switch (configKey) {
    case "odoo":
      return <IntegrationForm provider="odoo" title="Odoo ERP" />;
    case "whatsapp":
      return <IntegrationForm provider="whatsapp_cloud" title="WhatsApp Cloud API" />;
    case "m365":
      return <IntegrationForm provider="microsoft365" title="Microsoft 365" />;
    case "dgcp":
      return <IntegrationForm provider="dgcp" title="DGCP / Compras Públicas" />;
    case "ia":
      return <HermesAIConfigPanel />;
    case "prompts":
      return <HermesPromptsAdminPanel />;
    case "apariencia":
      return <AppearanceSettings />;
    case "permisos":
      return <CopilotPermissionsPanel />;
    case "integraciones":
      return (
        <Card>
          <CardHeader><CardTitle className="text-base">Integraciones</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Link href="/configuracion/integraciones" className="text-primary hover:underline">Centro de integraciones →</Link>
          </CardContent>
        </Card>
      );
    case "general":
      return (
        <Card>
          <CardHeader><CardTitle className="text-base">Configuración general</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <Link href="/configuracion" className="text-primary hover:underline">Panel de administración →</Link>
          </CardContent>
        </Card>
      );
    case "empresas":
      return (
        <Card>
          <CardContent className="py-4 text-sm">
            <Link href="/configuracion/empresas" className="text-primary hover:underline">Gestión de empresas del tenant →</Link>
          </CardContent>
        </Card>
      );
    case "usuarios":
      return (
        <Card>
          <CardContent className="py-4 text-sm">
            <Link href="/configuracion/usuarios" className="text-primary hover:underline">Usuarios y roles →</Link>
          </CardContent>
        </Card>
      );
    case "seguridad":
      return (
        <Card>
          <CardContent className="py-4 text-sm">
            <Link href="/configuracion/seguridad" className="text-primary hover:underline">Seguridad →</Link>
          </CardContent>
        </Card>
      );
    case "auditoria":
      return (
        <Card>
          <CardContent className="py-4 text-sm">
            <Link href="/configuracion/auditoria" className="text-primary hover:underline">Auditoría →</Link>
          </CardContent>
        </Card>
      );
    default:
      return null;
  }
}
