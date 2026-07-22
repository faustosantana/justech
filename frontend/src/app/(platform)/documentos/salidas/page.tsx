"use client";

import Link from "next/link";
import { Send } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function DocumentosSalidasPage() {
  return (
    <AppShell title="Expedientes y salidas" description="Carpeta SALIDAS en OneDrive — expedientes generados">
      <Card>
        <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
          <Send className="h-10 w-10 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground max-w-md">
            Los expedientes y documentos de salida se almacenan en{" "}
            <code className="text-xs">Justech-AI/SALIDAS</code>. Configure la carpeta en Repositorios y sincronice.
          </p>
          <Button size="sm" variant="outline" asChild>
            <Link href="/documentos/repositorios">Configurar repositorio SALIDAS</Link>
          </Button>
        </CardContent>
      </Card>
    </AppShell>
  );
}
