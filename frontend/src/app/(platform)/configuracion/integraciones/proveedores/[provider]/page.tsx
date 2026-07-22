"use client";

import Link from "next/link";
import { notFound } from "next/navigation";
import { use } from "react";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { SupplierIntegrationPanel } from "@/components/settings/supplier-integration-panel";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const LABELS: Record<string, string> = {
  ingram: "Ingram Micro",
  omega: "Omega Tech",
  intcomex: "Intcomex",
  tecnomarket: "Tecnomarket",
  cecomsa: "Cecomsa",
  tecnosinergia: "Tecnosinergia",
};

const COMING_SOON = new Set(["intcomex", "tecnomarket", "tecnosinergia"]);

export default function ProveedorDetailPage({ params }: { params: Promise<{ provider: string }> }) {
  const { provider } = use(params);
  const label = LABELS[provider];

  if (!label) notFound();

  if (COMING_SOON.has(provider)) {
    return (
      <div>
        <AdminPageHeader title={label} description="Integración en desarrollo" />
        <Card>
          <CardContent className="py-8 text-center text-sm text-muted-foreground">
            Este proveedor estará disponible en una próxima versión.
            <div className="mt-4">
              <Button variant="outline" size="sm" asChild>
                <Link href="/configuracion/integraciones/proveedores">← Volver</Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div>
      <AdminPageHeader
        title={label}
        description="Credenciales, sesión, MFA y prueba de conexión"
        action={
          <Button variant="outline" size="sm" asChild>
            <Link href="/configuracion/integraciones/proveedores">← Proveedores</Link>
          </Button>
        }
      />
      <SupplierIntegrationPanel provider={provider} title={label} />
    </div>
  );
}
