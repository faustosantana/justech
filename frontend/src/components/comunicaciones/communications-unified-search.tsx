"use client";

import {
  Building2,
  FileText,
  History,
  Loader2,
  Mail,
  MessageCircle,
  Search,
  Users,
  Video,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api";
import type { CommunicationsUnifiedSearchResult, HubChannelFilter } from "@/lib/communications";
import { cn } from "@/lib/utils";

const CHANNEL_FILTERS: { id: HubChannelFilter; label: string; icon: typeof Search }[] = [
  { id: "all", label: "Todo", icon: Search },
  { id: "whatsapp", label: "WhatsApp", icon: MessageCircle },
  { id: "outlook", label: "Outlook", icon: Mail },
  { id: "teams", label: "Teams", icon: Video },
  { id: "enterprise", label: "Empresa", icon: Building2 },
  { id: "documents", label: "Documentos", icon: FileText },
];

const GROUP_ICONS: Record<string, typeof Mail> = {
  whatsapp_chats: MessageCircle,
  whatsapp_messages: MessageCircle,
  outlook_mail: Mail,
  teams: Video,
  m365_files: FileText,
  customers: Users,
  dgcp: FileText,
  tasks: History,
};

function channelColor(channel: string) {
  const map: Record<string, string> = {
    whatsapp: "border-emerald-500/30 bg-emerald-500/5 text-emerald-700",
    outlook: "border-sky-500/30 bg-sky-500/5 text-sky-700",
    teams: "border-violet-500/30 bg-violet-500/5 text-violet-700",
    m365: "border-indigo-500/30 bg-indigo-500/5 text-indigo-700",
  };
  return map[channel] || "border-border bg-muted/30 text-muted-foreground";
}

function formatWhen(iso?: string | null) {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleString("es-DO", { dateStyle: "short", timeStyle: "short" });
}

type Props = {
  initialQuery?: string;
  compact?: boolean;
};

export function CommunicationsUnifiedSearch({ initialQuery = "", compact = false }: Props) {
  const [query, setQuery] = useState(initialQuery);
  const [filter, setFilter] = useState<HubChannelFilter>("all");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CommunicationsUnifiedSearchResult | null>(null);

  const runSearch = useCallback(async (q: string, ch: HubChannelFilter) => {
    const trimmed = q.trim();
    if (trimmed.length < 2) {
      setResult(null);
      return;
    }
    setLoading(true);
    try {
      const channel = ch === "all" ? undefined : ch;
      const res = await apiClient.searchCommunications(trimmed, channel);
      setResult(res);
    } catch {
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (initialQuery && initialQuery.length >= 2) {
      setQuery(initialQuery);
      runSearch(initialQuery, filter);
    }
  }, [initialQuery, filter, runSearch]);

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    runSearch(query, filter);
  };

  return (
    <div className="space-y-4">
      <form onSubmit={onSubmit} className="flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='Buscar en todo JAIOS — ej. "Banco ADEMI", "licitación laptops"…'
            className="h-11 pl-9"
          />
        </div>
        <Button type="submit" disabled={loading || query.trim().length < 2} className="h-11 bg-emerald-600 hover:bg-emerald-700">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Buscar"}
        </Button>
      </form>

      <div className="flex flex-wrap gap-1.5">
        {CHANNEL_FILTERS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => {
              setFilter(id);
              if (query.trim().length >= 2) runSearch(query, id);
            }}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition",
              filter === id ? "bg-foreground text-background" : "bg-muted/60 text-muted-foreground hover:bg-muted",
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </button>
        ))}
      </div>

      {!result && !loading && query.trim().length < 2 && !compact && (
        <div className="rounded-2xl border bg-gradient-to-br from-sky-500/5 via-background to-emerald-500/5 py-16 text-center">
          <Search className="mx-auto mb-3 h-10 w-10 text-muted-foreground/60" />
          <h3 className="text-lg font-semibold">Búsqueda omnicanal</h3>
          <p className="mx-auto mt-2 max-w-lg text-sm text-muted-foreground">
            Un solo lugar para encontrar correos Outlook, chats WhatsApp, Teams, documentos, clientes Odoo,
            licitaciones DGCP y tareas — todo relacionado con tu consulta.
          </p>
        </div>
      )}

      {result && (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            {result.total} resultados en {result.latency_ms ?? "?"} ms — fuentes: {result.sources_searched.join(", ") || "—"}
          </p>

          {result.timeline.length > 0 && (
            <div className="rounded-2xl border bg-card/50 p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
                <History className="h-4 w-4" /> Línea de tiempo
              </div>
              <div className="space-y-2">
                {result.timeline.slice(0, 12).map((item) => (
                  <Link
                    key={`${item.channel}-${item.id}`}
                    href={item.url}
                    className="flex gap-3 rounded-xl border bg-background/80 p-3 transition hover:border-emerald-500/30 hover:bg-emerald-500/5"
                  >
                    <span className={cn("mt-0.5 shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase", channelColor(item.channel))}>
                      {item.channel}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{item.title}</p>
                      {item.preview && <p className="truncate text-xs text-muted-foreground">{item.preview}</p>}
                      <p className="mt-1 text-[10px] text-muted-foreground">{formatWhen(item.timestamp)}</p>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          <div className="grid gap-4 lg:grid-cols-2">
            {result.groups.map((group) => {
              const Icon = GROUP_ICONS[group.type] || Search;
              return (
                <div key={group.type} className="rounded-2xl border bg-card/40 p-4 shadow-sm">
                  <div className="mb-3 flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm font-semibold">
                      <Icon className="h-4 w-4 text-emerald-600" />
                      {group.label}
                    </div>
                    <span className="rounded-full bg-muted px-2 py-0.5 text-xs">{group.count}</span>
                  </div>
                  <div className="space-y-2">
                    {group.items.map((item) => (
                      <Link
                        key={item.id}
                        href={item.url}
                        className="block rounded-xl border bg-background p-3 transition hover:border-primary/30"
                      >
                        <p className="text-sm font-medium leading-snug">{item.title}</p>
                        {item.subtitle && <p className="mt-0.5 text-xs text-muted-foreground">{item.subtitle}</p>}
                        {item.description && (
                          <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{item.description}</p>
                        )}
                      </Link>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          {result.total === 0 && (
            <p className="py-8 text-center text-sm text-muted-foreground">Sin resultados para «{result.query}».</p>
          )}
        </div>
      )}
    </div>
  );
}
