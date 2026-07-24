"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { MotorToolIntro } from "@/components/lottery/control-center/motor-tool-intro";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

const STATUS_LABELS = [
  "Cálculo verificado",
  "Histórico localizado",
  "Relación confirmada",
  "Sin confirmación",
  "Seguimiento incompleto",
];

export default function AuditoriaPage() {
  const [number, setNumber] = useState("35");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const href = useMemo(() => {
    const params = new URLSearchParams({ auto: "1", featured: "1" });
    const n = Number(number);
    if (Number.isInteger(n) && n >= 1 && n <= 100) params.set("number", String(n));
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    return `/lottery/admin/control-center/motor/historial-numero?${params.toString()}`;
  }, [number, dateFrom, dateTo]);

  return (
    <div className="space-y-4">
      <MotorToolIntro
        title="Auditoría"
        description="Busque un número y abra su expediente auditado: qué salió, qué compañeros se revisaron, qué confirmadores aparecieron, cuál se fortaleció y qué pasó después."
      />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Buscar expediente auditado</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-4">
          <label className="text-sm">
            Número
            <Input className="mt-1" value={number} onChange={(e) => setNumber(e.target.value)} inputMode="numeric" />
          </label>
          <label className="text-sm">
            Desde
            <Input className="mt-1" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </label>
          <label className="text-sm">
            Hasta
            <Input className="mt-1" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </label>
          <div className="flex items-end">
            <Button asChild className="min-h-11 w-full">
              <Link href={href}>Abrir expediente</Link>
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Estados visibles</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2 text-sm">
          {STATUS_LABELS.map((s) => (
            <span key={s} className="rounded-full border px-3 py-1">
              {s}
            </span>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Cómo se verifica</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            Cada caso ancla en un <strong>sorteo real</strong> (identidad = draw_id). El JSON técnico
            permanece oculto por defecto dentro del expediente.
          </p>
          <p>
            La fuerza siempre pertenece al <strong>compañero de Tabla 1</strong>; el confirmador de
            Tabla 2 aporta evidencia, no se fortalece a sí mismo.
          </p>
          <div className="flex flex-wrap gap-2 pt-2">
            <Link
              className="inline-block rounded border px-3 py-1.5 text-foreground hover:bg-muted"
              href="/lottery/admin/control-center/motor/historial-numero"
            >
              Historial del Número
            </Link>
            <Link
              className="inline-block rounded border px-3 py-1.5 text-foreground hover:bg-muted"
              href="/lottery/admin/control-center/motor/relaciones"
            >
              Relaciones
            </Link>
            <Link
              className="inline-block rounded border px-3 py-1.5 text-foreground hover:bg-muted"
              href="/lottery/admin/lotteries"
            >
              Administración de loterías
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
