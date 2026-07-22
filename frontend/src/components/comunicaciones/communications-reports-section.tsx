"use client";

import { useEffect, useState } from "react";

import { ModuleKpiGrid } from "@/components/module/module-dashboard";
import { ModuleActivityTimeline } from "@/components/module/module-dashboard";
import { apiClient } from "@/lib/api";
import type { ModuleActivity, ModuleKpi } from "@/lib/modules/types";
import { moduleSectionHref } from "@/lib/modules/types";

export function CommunicationsReportsSection() {
  const [kpis, setKpis] = useState<ModuleKpi[]>([]);
  const [activity, setActivity] = useState<ModuleActivity[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [conversations, observations, hub] = await Promise.allSettled([
          apiClient.listWhatsappConversations(),
          apiClient.listObservations({ limit: 10 }),
          apiClient.getCommunicationsHubStatus(),
        ]);

        const chats = conversations.status === "fulfilled" ? conversations.value.items : [];
        const obs = observations.status === "fulfilled" ? observations.value.items : [];
        const unread = chats.filter((c) => c.unread_count > 0).length;

        setKpis([
          { id: "open", label: "Conversaciones", value: String(chats.length), href: moduleSectionHref("comunicaciones", "conversaciones") },
          { id: "unread", label: "Sin responder", value: String(unread), tone: unread > 0 ? "warning" : "default" },
          { id: "obs", label: "Detecciones IA", value: String(observations.status === "fulfilled" ? observations.value.total : 0), href: moduleSectionHref("comunicaciones", "bandejas") },
          { id: "wa", label: "WhatsApp", value: hub.status === "fulfilled" ? hub.value.whatsapp.status : "—", tone: "success" },
          { id: "ol", label: "Outlook", value: hub.status === "fulfilled" ? hub.value.outlook.status : "—" },
        ]);

        setActivity([
          ...obs.slice(0, 5).map((o) => ({
            id: o.id,
            title: o.summary,
            subtitle: `${o.channel} · ${o.status}`,
          })),
          ...chats.slice(0, 5).map((c) => ({
            id: c.id,
            title: c.name || c.phone_number || "Chat",
            subtitle: c.last_message_preview || undefined,
            href: moduleSectionHref("comunicaciones", "conversaciones"),
          })),
        ]);
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, []);

  if (loading) return <p className="text-sm text-muted-foreground">Cargando reportes…</p>;

  return (
    <div className="space-y-8">
      <section>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">Indicadores del módulo</h2>
        <ModuleKpiGrid kpis={kpis} />
      </section>
      <section className="rounded-2xl border border-border/60 bg-card/80 p-5">
        <h2 className="mb-4 text-xs font-semibold uppercase tracking-widest text-muted-foreground">Actividad reciente</h2>
        <ModuleActivityTimeline items={activity.slice(0, 12)} />
      </section>
    </div>
  );
}
