"use client";

import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function AuditoriaPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Motor Matemático · Auditoría</h1>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Trazabilidad por draw_id</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            Cada punto del ranking en{" "}
            <Link className="underline" href="/lottery/admin/control-center/motor/relaciones">
              Relaciones
            </Link>{" "}
            se expande para mostrar: observed_number, draw_id, lotería, fecha/hora, posición,
            peers, mother_code, companion, table2_code/group, neighbor, score_delta, dedupe key.
          </p>
          <p>
            El JSON bruto está oculto por defecto; use «Ver JSON» (administradores) en cada traza.
          </p>
          <p>
            Identidad de sorteo = <code>draw_id</code>. El motor no altera histórico ni fórmulas.
          </p>
          <Link
            className="inline-block rounded border px-3 py-1.5 text-foreground hover:bg-muted"
            href="/lottery/admin/control-center/motor/relaciones"
          >
            Ir a Relaciones / traza
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
