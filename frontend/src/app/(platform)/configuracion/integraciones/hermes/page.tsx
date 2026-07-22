"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { IntegrationForm } from "@/components/settings/integration-form";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function HermesIntegracionPage() {
  return (
    <div>
      <AdminPageHeader
        title="Hermes — Integración de servicio"
        description="URL interna, token y conexión del microservicio Hermes"
        action={
          <Button size="sm" asChild>
            <Link href="/configuracion/ia/hermes">
              IA — Modelos y Prompts <ArrowRight className="ml-1 h-3.5 w-3.5" />
            </Link>
          </Button>
        }
      />
      <Card className="mb-6">
        <CardContent className="py-4 text-sm text-muted-foreground">
          Para configurar <strong>DeepSeek V4 Flash</strong>, system prompts, pruebas de modelo y diagnóstico del Copiloto, use{" "}
          <Link href="/configuracion/ia/hermes" className="text-primary underline">
            Configuración → IA — Hermes / Modelos
          </Link>
          .
        </CardContent>
      </Card>
      <IntegrationForm provider="hermes" title="Conexión del servicio Hermes" showLogs />
    </div>
  );
}
