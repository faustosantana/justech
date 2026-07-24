import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const CARDS = [
  {
    title: "Motor Matemático",
    href: "/lottery/admin/control-center/motor/table1",
    body: "Ver fórmulas, Tabla 1/2, agrupaciones, relaciones y trazabilidad. Solo lectura del motor v1.0.0.",
  },
  {
    title: "Predicciones",
    href: "/lottery/admin/control-center/predicciones",
    body: "Activar/desactivar motores implementados. Predicción real = presentación del ranking histórico NR.",
  },
  {
    title: "Prompt Studio",
    href: "/lottery/admin/control-center/prompt-studio",
    body: "Bloques con ayuda, prompt compilado, borradores, versiones humanas, playground y benchmark.",
  },
];

export default function ControlCenterHubPage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Lottery IA Control Center</h1>
        <p className="text-sm text-muted-foreground">
          Plataforma administrativa: conocimiento, reglas y motores auditables. No modifica sync ni
          Producción.
        </p>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {CARDS.map((c) => (
          <Link key={c.href} href={c.href}>
            <Card className="h-full transition hover:border-primary/50">
              <CardHeader>
                <CardTitle className="text-base">{c.title}</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-muted-foreground">{c.body}</CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
