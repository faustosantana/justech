"use client";

import Link from "next/link";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { IntegrationForm } from "@/components/settings/integration-form";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function OdooIntegracionPage() {
  return (
    <div>
      <AdminPageHeader title="Odoo ERP" description="URL, base de datos, usuario API y modo lectura/escritura" />
      <div className="space-y-6">
        <IntegrationForm provider="odoo" showCompanies />
        <Card>
          <CardHeader><CardTitle className="text-base">Vinculación de usuarios</CardTitle></CardHeader>
          <CardContent>
            <p className="mb-3 text-sm text-muted-foreground">Tras configurar la API global, cada usuario vincula su cuenta Odoo.</p>
            <Button variant="outline" asChild><Link href="/odoo/settings">Vincular usuarios</Link></Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
