"use client";

import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/** Sesiones redirige a Memoria — misma fuente de datos, UI amigable sin UUID obligatorio. */
export default function LotteryAISessionsPage() {
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Sesiones</h2>
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Buscar conversaciones</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p className="text-muted-foreground">
            La inspección de sesiones (usuario, correo, loterías, números, timeline) está en{" "}
            <strong>Memoria</strong>. No se requiere UUID para buscar.
          </p>
          <Button asChild size="sm">
            <Link href="/lottery/admin/ai/memory">Ir a Memoria</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
