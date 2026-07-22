"use client";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { IntegrationForm } from "@/components/settings/integration-form";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function WhatsAppIntegracionPage() {
  return (
    <div>
      <AdminPageHeader title="WhatsApp" description="Cloud API (Meta) y sesión Web" />
      <div className="space-y-6">
        <IntegrationForm provider="whatsapp_cloud" title="WhatsApp Cloud API" />
        <Card>
          <CardHeader><CardTitle className="text-base">WhatsApp Web</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>La sesión por QR se gestiona desde el módulo operativo de WhatsApp.</p>
            <p>
              Webhook bridge:{" "}
              <code className="rounded bg-muted px-1">/api/v1/webhooks/whatsapp/bridge</code>
            </p>
            <p>
              Webhook Cloud API:{" "}
              <code className="rounded bg-muted px-1">/api/v1/webhooks/whatsapp</code>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
