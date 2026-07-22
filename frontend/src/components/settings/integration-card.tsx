"use client";

import Link from "next/link";
import { Plug, RefreshCw, Settings2, Unplug } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConnectionStatusBadge } from "@/components/settings/connection-status-badge";
import type { IntegrationCard as IntegrationCardType } from "@/lib/settings";

type TestFeedback = {
  ok: boolean;
  message: string;
  missing_config?: string[];
  latency_ms?: number;
};

type Props = {
  item: IntegrationCardType & { model?: string | null };
  onTest?: () => void;
  onDisconnect?: () => void;
  testing?: boolean;
  configureHref?: string;
  testFeedback?: TestFeedback;
  documentation?: string | null;
};

export function IntegrationCard({
  item,
  onTest,
  onDisconnect,
  testing,
  configureHref,
  testFeedback,
  documentation,
}: Props) {
  const href = configureHref || `/configuracion/integraciones/${item.provider}`;
  const statusMessage =
    testFeedback?.message ||
    item.last_test_message ||
    (item.credentials_configured ? "Credenciales configuradas" : "Sin configurar — revise campos requeridos");

  return (
    <Card className="flex flex-col">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <Plug className="h-4 w-4 text-primary" />
            {item.label}
          </CardTitle>
          <ConnectionStatusBadge
            status={item.status}
            connected={item.connected}
            configured={item.credentials_configured}
          />
        </div>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-3 text-sm">
        {item.model && (
          <p className="text-xs text-muted-foreground">
            Modelo: <span className="font-medium text-foreground">{item.model}</span>
          </p>
        )}
        {documentation && (
          <p className="text-xs text-muted-foreground line-clamp-2" title={documentation}>
            {documentation}
          </p>
        )}
        <p
          className={
            testFeedback
              ? testFeedback.ok
                ? "text-emerald-700"
                : "text-destructive"
              : "text-muted-foreground"
          }
        >
          {statusMessage}
        </p>
        {testFeedback?.missing_config && testFeedback.missing_config.length > 0 && (
          <p className="text-xs text-destructive">
            Falta: {testFeedback.missing_config.join(", ")}
          </p>
        )}
        {testFeedback?.latency_ms != null && (
          <p className="text-xs text-muted-foreground">Latencia: {testFeedback.latency_ms} ms</p>
        )}
        {item.last_test_at && !testFeedback && (
          <p className="text-xs text-muted-foreground">
            Último chequeo: {new Date(item.last_test_at).toLocaleString("es-DO")}
          </p>
        )}
        <div className="mt-auto flex flex-wrap gap-2">
          <Button size="sm" variant="outline" asChild>
            <Link href={href}>
              <Settings2 className="mr-1 h-3.5 w-3.5" />
              Configurar
            </Link>
          </Button>
          {onTest && (
            <Button size="sm" variant="outline" onClick={onTest} disabled={testing}>
              <RefreshCw className={`mr-1 h-3.5 w-3.5 ${testing ? "animate-spin" : ""}`} />
              Probar
            </Button>
          )}
          {onDisconnect && item.connected && (
            <Button size="sm" variant="ghost" onClick={onDisconnect}>
              <Unplug className="mr-1 h-3.5 w-3.5" />
              Desconectar
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
