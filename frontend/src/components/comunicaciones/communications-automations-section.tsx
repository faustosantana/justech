"use client";

import Link from "next/link";
import { Brain, Sparkles, Workflow } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";

export function CommunicationsAutomationsSection() {
  const [pending, setPending] = useState(0);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    apiClient
      .listObservations({ status: "pending_review", limit: 1 })
      .then((r) => {
        setPending(r.total);
        return apiClient.listObservations({ limit: 1 });
      })
      .then((r) => setTotal(r.total))
      .catch(() => {});
  }, []);

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Detecciones pendientes</CardDescription>
            <CardTitle className="text-2xl tabular-nums">{pending}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total observaciones</CardDescription>
            <CardTitle className="text-2xl tabular-nums">{total}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Motor IA</CardDescription>
            <CardTitle className="text-base">Hermes activo</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Sparkles className="h-4 w-4 text-primary" />
              Bandeja inteligente
            </CardTitle>
            <CardDescription>Automatizaciones de detección en WhatsApp y correo</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild size="sm">
              <Link href="/apps/comunicaciones/bandejas">Ver bandeja</Link>
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Brain className="h-4 w-4" />
              Prompts Hermes
            </CardTitle>
            <CardDescription>Ajusta comportamiento del copiloto por módulo</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild size="sm" variant="outline">
              <Link href="/configuracion/ia/prompts">Configurar prompts</Link>
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Workflow className="h-4 w-4" />
              Flujos n8n
            </CardTitle>
            <CardDescription>Automatizaciones externas conectadas al tenant</CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild size="sm" variant="outline">
              <Link href="/configuracion/integraciones">Integraciones</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
