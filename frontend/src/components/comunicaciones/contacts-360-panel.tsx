"use client";

import {
  Building2,
  Loader2,
  Mail,
  MessageCircle,
  Phone,
  RefreshCw,
  Search,
  Sparkles,
  User,
  Users,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api";
import type { UnifiedContact, UnifiedContactProfile360 } from "@/lib/communications";
import { cn } from "@/lib/utils";

const SOURCE_COLORS: Record<string, string> = {
  outlook: "bg-sky-500/15 text-sky-700",
  whatsapp: "bg-emerald-500/15 text-emerald-700",
  odoo: "bg-violet-500/15 text-violet-700",
  teams: "bg-indigo-500/15 text-indigo-700",
  dgcp: "bg-amber-500/15 text-amber-800",
};

function SourceBadge({ source }: { source: string }) {
  return (
    <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-medium uppercase", SOURCE_COLORS[source] || "bg-muted")}>
      {source}
    </span>
  );
}

export function Contacts360Panel() {
  const [query, setQuery] = useState("");
  const [contacts, setContacts] = useState<UnifiedContact[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [profile, setProfile] = useState<UnifiedContactProfile360 | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [profileLoading, setProfileLoading] = useState(false);

  const loadContacts = useCallback(async (q: string) => {
    setLoading(true);
    try {
      const res = await apiClient.listUnifiedContacts(q, true);
      setContacts(res.items);
      if (!selectedId && res.items.length > 0) {
        setSelectedId(res.items[0].id);
      }
    } finally {
      setLoading(false);
    }
  }, [selectedId]);

  const loadProfile = useCallback(async (id: string) => {
    setProfileLoading(true);
    try {
      const p = await apiClient.getUnifiedContactProfile(id);
      setProfile(p);
    } catch {
      setProfile(null);
    } finally {
      setProfileLoading(false);
    }
  }, []);

  useEffect(() => {
    loadContacts("");
  }, [loadContacts]);

  useEffect(() => {
    if (selectedId) loadProfile(selectedId);
  }, [selectedId, loadProfile]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await apiClient.syncUnifiedContacts();
      await loadContacts(query);
    } finally {
      setSyncing(false);
    }
  };

  const onSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadContacts(query);
  };

  return (
    <div className="flex h-[calc(100vh-14rem)] overflow-hidden rounded-2xl border shadow-sm">
      {/* Lista */}
      <div className="flex w-80 shrink-0 flex-col border-r bg-gradient-to-b from-violet-500/[0.04] to-background">
        <div className="border-b p-3">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold">Contactos unificados</h3>
            <Button size="icon" variant="ghost" className="h-8 w-8" onClick={handleSync} disabled={syncing}>
              {syncing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            </Button>
          </div>
          <form onSubmit={onSearch} className="relative">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Buscar contacto o empresa…"
              className="h-9 pl-8"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </form>
        </div>
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <p className="p-4 text-sm text-muted-foreground">Cargando contactos…</p>
          ) : contacts.length === 0 ? (
            <div className="p-4 text-center text-sm text-muted-foreground">
              <p>Sin contactos sincronizados.</p>
              <Button size="sm" className="mt-3" onClick={handleSync}>
                Sincronizar fuentes
              </Button>
            </div>
          ) : (
            contacts.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => setSelectedId(c.id)}
                className={cn(
                  "flex w-full gap-3 border-b px-3 py-3 text-left transition hover:bg-muted/40",
                  selectedId === c.id && "bg-violet-500/8",
                )}
              >
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-violet-500/15 text-violet-700">
                  <User className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{c.display_name}</p>
                  {c.company_name && <p className="truncate text-xs text-muted-foreground">{c.company_name}</p>}
                  <div className="mt-1 flex flex-wrap gap-1">
                    {c.sources.slice(0, 3).map((s) => (
                      <SourceBadge key={s} source={s} />
                    ))}
                  </div>
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Perfil 360 */}
      <div className="min-w-0 flex-1 overflow-y-auto bg-gradient-to-br from-background via-background to-sky-500/[0.03]">
        {!selectedId || profileLoading ? (
          <div className="flex h-full items-center justify-center text-muted-foreground">
            {profileLoading ? <Loader2 className="h-6 w-6 animate-spin" /> : "Selecciona un contacto"}
          </div>
        ) : profile ? (
          <div className="space-y-4 p-6">
            <div className="rounded-2xl border bg-card/60 p-5 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h2 className="text-xl font-semibold">{profile.contact.display_name}</h2>
                  {profile.contact.company_name && (
                    <p className="mt-1 flex items-center gap-1 text-sm text-muted-foreground">
                      <Building2 className="h-4 w-4" /> {profile.contact.company_name}
                    </p>
                  )}
                  <div className="mt-3 flex flex-wrap gap-2">
                    {profile.contact.source_labels.map((label, i) => (
                      <SourceBadge key={label} source={profile.contact.sources[i] || label} />
                    ))}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2 text-center sm:grid-cols-4">
                  {(
                    [
                      ["WhatsApp", profile.stats.whatsapp_chats, MessageCircle],
                      ["Tareas", profile.stats.tasks, Sparkles],
                      ["DGCP", profile.stats.dgcp_opportunities, Building2],
                      ["Fuentes", profile.stats.linked_sources, Users],
                    ] as [string, number, LucideIcon][]
                  ).map(([label, val, Icon]) => (
                    <div key={String(label)} className="rounded-xl border bg-background/80 px-3 py-2">
                      <Icon className="mx-auto mb-1 h-4 w-4 text-muted-foreground" />
                      <p className="text-lg font-semibold">{val}</p>
                      <p className="text-[10px] text-muted-foreground">{label}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {profile.emails.map((e) => (
                  <p key={e} className="flex items-center gap-2 text-sm">
                    <Mail className="h-4 w-4 text-sky-600" /> {e}
                  </p>
                ))}
                {profile.phones.map((p) => (
                  <p key={p} className="flex items-center gap-2 text-sm">
                    <Phone className="h-4 w-4 text-emerald-600" /> {p}
                  </p>
                ))}
              </div>
            </div>

            {profile.odoo_summary && (
              <div className="rounded-2xl border border-violet-500/20 bg-violet-500/5 p-4">
                <h4 className="text-sm font-semibold">Odoo CRM</h4>
                <p className="mt-1 text-sm">
                  {String(profile.odoo_summary.name ?? "—")} — {String(profile.odoo_summary.open_opportunities ?? 0)} oportunidades,{" "}
                  {String(profile.odoo_summary.open_quotations ?? 0)} cotizaciones
                </p>
                <Link href={`/odoo/customers/${String(profile.odoo_summary.partner_id ?? "")}`} className="mt-2 inline-block text-sm text-primary hover:underline">
                  Ver en Odoo →
                </Link>
              </div>
            )}

            {profile.dgcp_opportunities.length > 0 && (
              <div className="rounded-2xl border p-4">
                <h4 className="mb-2 text-sm font-semibold">Licitaciones DGCP</h4>
                <div className="space-y-2">
                  {profile.dgcp_opportunities.map((o) => (
                    <Link key={o.id} href={o.url} className="block rounded-lg border bg-background/80 p-3 text-sm hover:border-amber-500/30">
                      <p className="font-medium">{o.title}</p>
                      <p className="text-xs text-muted-foreground">{o.code} · {o.institution}</p>
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {profile.identities.length > 0 && (
              <div className="rounded-2xl border p-4">
                <h4 className="mb-2 text-sm font-semibold">Identidades vinculadas</h4>
                <div className="grid gap-2 sm:grid-cols-2">
                  {profile.identities.map((id) => (
                    <div key={id.id} className="rounded-xl border bg-background/60 p-3 text-sm">
                      <div className="flex items-center justify-between">
                        <SourceBadge source={id.source} />
                        {id.profile_url && (
                          <Link href={id.profile_url} className="text-xs text-primary hover:underline">
                            Abrir
                          </Link>
                        )}
                      </div>
                      <p className="mt-1 font-medium">{id.display_name}</p>
                      {id.email && <p className="text-xs text-muted-foreground">{id.email}</p>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {profile.timeline.length > 0 && (
              <div className="rounded-2xl border p-4">
                <h4 className="mb-2 text-sm font-semibold">Actividad reciente</h4>
                <div className="space-y-2">
                  {profile.timeline.slice(0, 8).map((t) => (
                    <Link key={`${t.channel}-${t.id}`} href={t.url} className="flex gap-2 rounded-lg border p-2 text-sm hover:bg-muted/30">
                      <SourceBadge source={t.channel} />
                      <div className="min-w-0">
                        <p className="truncate font-medium">{t.title}</p>
                        {t.preview && <p className="truncate text-xs text-muted-foreground">{t.preview}</p>}
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
