"use client";

import Link from "next/link";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { IntegrationForm } from "@/components/settings/integration-form";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function M365IntegracionPage() {
  return (
    <div>
      <AdminPageHeader title="Microsoft 365" description="Azure AD, Graph API y OAuth de usuarios" />
      <div className="space-y-6">
        <IntegrationForm provider="microsoft365" />
        <Card>
          <CardHeader><CardTitle className="text-base">Cuentas de usuario</CardTitle></CardHeader>
          <CardContent className="flex gap-2">
            <Button asChild><Link href="/m365/cuentas">Conectar cuenta Microsoft</Link></Button>
            <Button variant="outline" asChild><Link href="/m365">Espacio M365</Link></Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
