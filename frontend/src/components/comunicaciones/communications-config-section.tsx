"use client";

import Link from "next/link";

import { IntegrationForm } from "@/components/settings/integration-form";
import { WhatsappSessionsPanel } from "@/components/comunicaciones/whatsapp-sessions-panel";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function CommunicationsConfigSection() {
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <IntegrationForm provider="whatsapp_cloud" title="WhatsApp Cloud API" />
      <Card>
        <CardHeader>
          <CardTitle className="text-base">WhatsApp Web (sesiones QR)</CardTitle>
        </CardHeader>
        <CardContent>
          <WhatsappSessionsPanel />
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Microsoft 365</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>Outlook y Teams se configuran en la integración M365.</p>
          <Link href="/configuracion/integraciones/microsoft365" className="text-primary hover:underline">
            Configuración M365 →
          </Link>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="space-y-2 py-4 text-sm text-muted-foreground">
          <p>
            Webhook bridge:{" "}
            <code className="rounded bg-muted px-1">/api/v1/webhooks/whatsapp/bridge</code>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
