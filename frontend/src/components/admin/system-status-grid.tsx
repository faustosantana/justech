"use client";

import Link from "next/link";
import { ExternalLink, FileText, RefreshCw, Settings2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConnectionStatusBadge } from "@/components/settings/connection-status-badge";
import type { IntegrationStatus } from "@/lib/settings";
import { cn } from "@/lib/utils";

export interface StatusGridItem {
  id: string;
  name: string;
  status: string;
  message?: string | null;
  config_url?: string;
  is_dynamic?: boolean;
  onTest?: () => void;
  testing?: boolean;
}

export function SystemStatusGrid({ items }: { items: StatusGridItem[] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {items.map((item) => (
        <Card key={item.id} className="flex flex-col">
          <CardHeader className="pb-2">
            <div className="flex items-start justify-between gap-2">
              <CardTitle className="text-sm font-medium">{item.name}</CardTitle>
              <ConnectionStatusBadge
                status={
                  (item.status === "connected" || item.status === "ok"
                    ? "connected"
                    : item.status === "configured"
                      ? "configured"
                      : item.status === "credential_error"
                        ? "credential_error"
                        : "not_configured") as IntegrationStatus
                }
              />
            </div>
          </CardHeader>
          <CardContent className="mt-auto space-y-3">
            <p className={cn("text-sm", item.message ? "text-muted-foreground" : "text-muted-foreground/60")}>
              {item.message || "Sin información"}
            </p>
            <div className="flex flex-wrap gap-2">
              {item.config_url && (
                <Button size="sm" variant="outline" asChild>
                  <Link href={item.config_url}>
                    <Settings2 className="mr-1 h-3.5 w-3.5" />
                    Configurar
                  </Link>
                </Button>
              )}
              {item.onTest && (
                <Button size="sm" variant="outline" onClick={item.onTest} disabled={item.testing}>
                  <RefreshCw className={cn("mr-1 h-3.5 w-3.5", item.testing && "animate-spin")} />
                  Probar
                </Button>
              )}
              {item.is_dynamic && (
                <Button size="sm" variant="ghost" asChild>
                  <Link href={`/configuracion/apis/${item.id}`}>
                    <ExternalLink className="mr-1 h-3.5 w-3.5" />
                    Ver
                  </Link>
                </Button>
              )}
              <Button size="sm" variant="ghost" asChild>
                <Link href="/configuracion/auditoria">
                  <FileText className="mr-1 h-3.5 w-3.5" />
                  Logs
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
