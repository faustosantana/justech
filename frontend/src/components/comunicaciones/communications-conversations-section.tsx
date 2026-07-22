"use client";

import { Mail, MessageCircle, Search, Video } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo } from "react";

import { CommunicationsUnifiedSearch } from "@/components/comunicaciones/communications-unified-search";
import { WhatsappInbox } from "@/components/comunicaciones/whatsapp-inbox";
import { LoadingState } from "@/components/brand/loading-state";
import { M365Workspace } from "@/components/m365/m365-workspace";
import { cn } from "@/lib/utils";

const CHANNELS = [
  { id: "whatsapp", label: "WhatsApp", icon: MessageCircle },
  { id: "outlook", label: "Outlook", icon: Mail },
  { id: "teams", label: "Teams", icon: Video },
  { id: "historial", label: "Historial", icon: Search },
] as const;

type ChannelId = (typeof CHANNELS)[number]["id"];

type Props = {
  activeView?: string;
};

function ConversationsInner({ activeView }: Props) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const canal = (searchParams.get("canal") as ChannelId) || "whatsapp";

  const setCanal = (id: ChannelId) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("canal", id);
    router.replace(`/apps/comunicaciones/conversaciones?${params.toString()}`);
  };

  const body = useMemo(() => {
    if (activeView === "kanban" && canal === "whatsapp") {
      return <WhatsappInbox variant="kanban" hideSessionManagement />;
    }
    switch (canal) {
      case "outlook":
        return <M365Workspace initialApp="outlook" embedded />;
      case "teams":
        return <M365Workspace initialApp="teams" embedded />;
      case "historial":
        return (
          <div className="max-w-3xl">
            <CommunicationsUnifiedSearch initialQuery={searchParams.get("q") ?? ""} />
          </div>
        );
      default:
        return <WhatsappInbox hideSessionManagement />;
    }
  }, [canal, activeView, searchParams]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-1 rounded-xl border border-border/60 bg-muted/30 p-1">
        {CHANNELS.map((c) => {
          const Icon = c.icon;
          return (
            <button
              key={c.id}
              type="button"
              onClick={() => setCanal(c.id)}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition",
                canal === c.id ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              {c.label}
            </button>
          );
        })}
      </div>
      {body}
    </div>
  );
}

export function CommunicationsConversationsSection({ activeView = "list" }: Props) {
  return (
    <Suspense fallback={<LoadingState message="Cargando conversaciones…" />}>
      <ConversationsInner activeView={activeView} />
    </Suspense>
  );
}
