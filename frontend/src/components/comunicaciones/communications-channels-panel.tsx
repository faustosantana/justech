"use client";

import Link from "next/link";
import { Mail, MessageCircle, RefreshCw, Sparkles, Video } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { WhatsappSessionsPanel } from "@/components/comunicaciones/whatsapp-sessions-panel";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import type { CommunicationsHubStatus, WhatsappSession } from "@/lib/communications";
import { cn } from "@/lib/utils";

function statusTone(status: string) {
  if (status === "connected" || status === "ok" || status === "ready") return "text-emerald-700 bg-emerald-500/10";
  if (status === "partial" || status === "degraded") return "text-amber-800 bg-amber-500/10";
  return "text-muted-foreground bg-muted";
}

export function CommunicationsChannelsPanel() {
  const [hub, setHub] = useState<CommunicationsHubStatus | null>(null);
  const [qrSession, setQrSession] = useState<WhatsappSession | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setHub(await apiClient.getCommunicationsHubStatus());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const channels = hub
    ? [
        { key: "whatsapp", label: "WhatsApp", icon: MessageCircle, data: hub.whatsapp },
        { key: "outlook", label: "Outlook", icon: Mail, data: hub.outlook },
        { key: "teams", label: "Teams", icon: Video, data: hub.teams },
        { key: "ai", label: "Copiloto IA", icon: Sparkles, data: hub.ai },
      ]
    : [];

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          <RefreshCw className={cn("mr-2 h-4 w-4", loading && "animate-spin")} />
          Actualizar estado
        </Button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {channels.map(({ key, label, icon: Icon, data }) => (
          <Card key={key}>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm font-medium">
                <Icon className="h-4 w-4" />
                {label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <span className={cn("inline-block rounded-full px-2 py-0.5 text-xs font-medium", statusTone(data.status))}>
                {data.status}
              </span>
              {data.detail && <p className="mt-2 text-xs text-muted-foreground">{data.detail}</p>}
              {key === "outlook" || key === "teams" ? (
                <Link
                  href={`/apps/comunicaciones/conversaciones?canal=${key}`}
                  className="mt-3 inline-block text-xs text-primary hover:underline"
                >
                  Abrir bandeja →
                </Link>
              ) : null}
            </CardContent>
          </Card>
        ))}
      </div>

      <WhatsappSessionsPanel onShowQr={setQrSession} />

      {qrSession?.qr_image && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Vincular WhatsApp Web — {qrSession.label}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col items-center gap-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={qrSession.qr_image} alt="QR WhatsApp" className="max-w-xs rounded-lg border" />
            <p className="text-center text-xs text-muted-foreground">
              Escanea con WhatsApp → Dispositivos vinculados. Al conectar, se sincronizan contactos y conversaciones.
            </p>
            <Button variant="outline" size="sm" onClick={() => setQrSession(null)}>
              Cerrar
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
