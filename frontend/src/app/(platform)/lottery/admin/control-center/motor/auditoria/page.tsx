"use client";

import Link from "next/link";

import { MotorToolIntro } from "@/components/lottery/control-center/motor-tool-intro";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function AuditoriaPage() {
  return (
    <div className="space-y-4">
      <MotorToolIntro
        title="Auditoría"
        description="Cómo se demuestra cada conclusión del motor: cada punto ancla en un draw_id real, sin mezclar sorteos por fecha."
      />
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Trazabilidad por sorteo</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            En{" "}
            <Link className="underline" href="/lottery/admin/control-center/motor/relaciones">
              Relaciones
            </Link>{" "}
            y en el{" "}
            <Link className="underline" href="/lottery/admin/control-center/motor/historial-numero">
              Historial del Número
            </Link>
            , cada caso muestra número observado, lotería, fecha, compañeros, confirmadores y qué
            ocurrió después.
          </p>
          <p>
            La evidencia técnica (JSON) permanece colapsada y solo para administradores. El motor no
            altera histórico ni fórmulas.
          </p>
          <div className="flex flex-wrap gap-2 pt-2">
            <Link
              className="inline-block rounded border px-3 py-1.5 text-foreground hover:bg-muted"
              href="/lottery/admin/control-center/motor/historial-numero"
            >
              Ir al Historial del Número
            </Link>
            <Link
              className="inline-block rounded border px-3 py-1.5 text-foreground hover:bg-muted"
              href="/lottery/admin/control-center/motor/relaciones"
            >
              Ir a Relaciones
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
