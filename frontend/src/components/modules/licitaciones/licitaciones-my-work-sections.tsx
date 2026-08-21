"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Loader2, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api";
import {
  formatRemaining,
  trafficDot,
  type HoyItem,
  type MyLicitacionRow,
  type MyWorkSummary,
  type PrepTask,
} from "@/lib/dgcp-my-work";
import { formatDateTime } from "@/lib/dgcp";
import { cn } from "@/lib/utils";

const LIGHT_LABEL: Record<string, string> = {
  green: ">5 días",
  yellow: "3–5 días",
  orange: "1–2 días",
  red: "<24h",
  black: "Vencida",
  none: "Sin fecha",
};

function SummaryCards({ summary }: { summary: MyWorkSummary }) {
  const cards = [
    { label: "Requieren atención hoy", value: summary.require_attention_today },
    { label: "Vencen en 3 días", value: summary.due_in_3_days },
    { label: "En preparación", value: summary.in_preparation },
    { label: "Pendientes vencidos", value: summary.overdue_tasks },
    { label: "Adjudicaciones nuevas", value: summary.new_awards },
  ];
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
      {cards.map((c) => (
        <div key={c.label} className="rounded-lg border bg-white px-3 py-3">
          <div className="text-2xl font-semibold text-slate-900">{c.value}</div>
          <div className="text-xs text-slate-500">{c.label}</div>
        </div>
      ))}
    </div>
  );
}

export function LicitacionesMisLicitacionesSection() {
  const [scope, setScope] = useState<"mine" | "team" | "unassigned" | "all">("mine");
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<MyLicitacionRow[]>([]);
  const [summary, setSummary] = useState<MyWorkSummary | null>(null);
  const [hoy, setHoy] = useState<HoyItem[]>([]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [lic, h] = await Promise.all([
        apiClient.getDGCPMyLicitaciones({ scope, q: q || undefined }),
        apiClient.getDGCPHoy(),
      ]);
      setItems(lic.items);
      setSummary(lic.summary);
      setHoy(h.items.slice(0, 8));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error cargando Mis Licitaciones");
    } finally {
      setLoading(false);
    }
  }, [scope, q]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-4 p-1">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Mis Licitaciones</h2>
          <p className="text-sm text-slate-500">Centro operativo diario — solo procesos en los que trabajas.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={() => void load()} disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          </Button>
          <Button size="sm" variant="outline" asChild>
            <Link href="/apps/licitaciones/mis-pendientes">Mis Pendientes</Link>
          </Button>
        </div>
      </div>

      {summary && <SummaryCards summary={summary} />}

      {hoy.length > 0 && (
        <div className="rounded-lg border bg-amber-50/60 p-3">
          <div className="mb-2 text-sm font-medium text-slate-800">Hoy</div>
          <ul className="space-y-1 text-sm">
            {hoy.map((h, i) => (
              <li key={`${h.kind}-${h.task_id || h.opportunity_id}-${i}`} className="flex flex-wrap gap-2">
                <span className="text-xs uppercase text-slate-500">{h.kind.replace(/_/g, " ")}</span>
                <Link href={`/dgcp/${h.opportunity_id}`} className="text-sky-700 hover:underline">
                  {h.title}
                </Link>
                <span className="text-slate-500">{h.opportunity_code}</span>
                {h.due_at && <span className="text-slate-500">{formatDateTime(h.due_at)}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        {(
          [
            ["mine", "Mías"],
            ["team", "Equipo"],
            ["unassigned", "Sin responsable"],
            ["all", "Todos"],
          ] as const
        ).map(([k, label]) => (
          <Button key={k} size="sm" variant={scope === k ? "default" : "outline"} onClick={() => setScope(k)}>
            {label}
          </Button>
        ))}
        <input
          className="min-w-[180px] flex-1 rounded border px-3 py-1.5 text-sm"
          placeholder="Buscar código, institución, pendiente…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && void load()}
        />
      </div>

      {error && <p className="text-sm text-amber-800">{error}</p>}
      {loading && !items.length && (
        <p className="flex items-center gap-2 text-sm text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" /> Cargando…
        </p>
      )}

      <div className="overflow-x-auto rounded border">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b bg-slate-50 text-left text-slate-500">
              <th className="p-2">Proceso</th>
              <th className="p-2">Empresa</th>
              <th className="p-2">Responsable</th>
              <th className="p-2">Estado</th>
              <th className="p-2">Deadline</th>
              <th className="p-2">Checklist</th>
              <th className="p-2">Próximo</th>
            </tr>
          </thead>
          <tbody>
            {items.map((r) => (
              <tr key={r.opportunity_id} className="border-b border-slate-100 align-top">
                <td className="p-2">
                  <Link href={`/dgcp/${r.opportunity_id}`} className="font-medium text-sky-700 hover:underline">
                    {r.code}
                  </Link>
                  <div className="text-xs text-slate-500">{r.institution}</div>
                </td>
                <td className="p-2 uppercase text-xs">{r.company}</td>
                <td className="p-2">{r.responsible_name || "—"}</td>
                <td className="p-2">{r.status_label}</td>
                <td className="p-2">
                  <div>
                    {trafficDot(r.process_traffic_light)} {formatDateTime(r.process_deadline)}
                  </div>
                  <div className="text-xs text-slate-500">
                    {formatRemaining(r.process_hours_remaining)} · {LIGHT_LABEL[r.process_traffic_light]}
                  </div>
                </td>
                <td className="p-2">
                  <div>
                    {r.checklist_progress.completed}/{r.checklist_progress.applicable}
                  </div>
                  <div className="mt-1 h-1.5 w-24 rounded bg-slate-100">
                    <div
                      className="h-1.5 rounded bg-sky-500"
                      style={{ width: `${Math.min(100, r.checklist_progress.pct)}%` }}
                    />
                  </div>
                </td>
                <td className="p-2">
                  {r.next_pending_title ? (
                    <>
                      <div>{r.next_pending_title}</div>
                      <div className="text-xs text-slate-500">{formatDateTime(r.next_pending_due_at)}</div>
                    </>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && !items.length && (
          <p className="p-4 text-sm text-slate-500">No hay licitaciones en este alcance.</p>
        )}
      </div>
    </div>
  );
}

export function LicitacionesMisPendientesSection() {
  const [filter, setFilter] = useState("open");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [items, setItems] = useState<PrepTask[]>([]);
  const [codes, setCodes] = useState<Record<string, string>>({});
  const [institutions, setInstitutions] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getDGCPMisPendientes({ filter_mode: filter });
      setItems(res.items);
      setCodes(res.opportunity_code || {});
      setInstitutions(res.institution || {});
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    void load();
  }, [load]);

  const toggle = async (id: string) => {
    await apiClient.toggleDGCPPrepTask(id);
    await load();
  };

  return (
    <div className="space-y-4 p-1">
      <h2 className="text-xl font-semibold">Mis Pendientes</h2>
      <div className="flex flex-wrap gap-2">
        {(
          [
            ["open", "Abiertos"],
            ["today", "Hoy"],
            ["overdue", "Vencidos"],
            ["week", "Esta semana"],
            ["completed", "Completados"],
          ] as const
        ).map(([k, label]) => (
          <Button key={k} size="sm" variant={filter === k ? "default" : "outline"} onClick={() => setFilter(k)}>
            {label}
          </Button>
        ))}
      </div>
      {error && <p className="text-sm text-amber-800">{error}</p>}
      {loading && <Loader2 className="h-4 w-4 animate-spin text-slate-400" />}
      <div className="overflow-x-auto rounded border">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b bg-slate-50 text-left text-slate-500">
              <th className="p-2 w-8" />
              <th className="p-2">Pendiente</th>
              <th className="p-2">Licitación</th>
              <th className="p-2">Institución</th>
              <th className="p-2">Deadline</th>
              <th className="p-2">Prioridad</th>
              <th className="p-2">Estado</th>
            </tr>
          </thead>
          <tbody>
            {items.map((t) => (
              <tr key={t.id} className="border-b border-slate-100">
                <td className="p-2">
                  <input
                    type="checkbox"
                    checked={t.status === "completed"}
                    onChange={() => void toggle(t.id)}
                    aria-label="Completar"
                  />
                </td>
                <td className="p-2 font-medium">{t.title}</td>
                <td className="p-2">
                  <Link href={`/dgcp/${t.opportunity_id}`} className="text-sky-700 hover:underline">
                    {codes[t.opportunity_id] || t.opportunity_id.slice(0, 8)}
                  </Link>
                </td>
                <td className="p-2">{institutions[t.opportunity_id] || "—"}</td>
                <td className="p-2">
                  {trafficDot(t.traffic_light)} {formatDateTime(t.due_at)}
                </td>
                <td className="p-2 capitalize">{t.priority}</td>
                <td className="p-2">{t.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && !items.length && <p className="p-4 text-sm text-slate-500">Sin pendientes.</p>}
      </div>
    </div>
  );
}

export function LicitacionesChecklistPlantillasSection() {
  const [templates, setTemplates] = useState<Awaited<ReturnType<typeof apiClient.listDGCPPrepTemplates>>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient
      .listDGCPPrepTemplates()
      .then(setTemplates)
      .catch(() => setTemplates([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-4 p-1">
      <h2 className="text-xl font-semibold">Plantillas de checklist</h2>
      <p className="text-sm text-slate-500">Plantillas operativas de preparación (no afectan el checklist documental).</p>
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      <div className="space-y-3">
        {templates.map((t) => (
          <div key={t.id} className="rounded border p-3">
            <div className="font-medium">
              {t.name} {t.is_default && <span className="text-xs text-sky-700">(predeterminada)</span>}
            </div>
            {t.description && <p className="text-sm text-slate-500">{t.description}</p>}
            <ul className="mt-2 list-disc pl-5 text-sm text-slate-700">
              {t.items.map((i) => (
                <li key={i.item_key}>
                  {i.title}{" "}
                  <span className="text-xs text-slate-400">
                    {i.priority}
                    {i.default_offset_hours != null ? ` · ${i.default_offset_hours}h vs deadline` : ""}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

export function DGCPPrepPanel({ opportunityId }: { opportunityId: string }) {
  const [data, setData] = useState<Awaited<ReturnType<typeof apiClient.getDGCPPrepChecklist>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await apiClient.getDGCPPrepChecklist(opportunityId));
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [opportunityId]);

  useEffect(() => {
    void load();
  }, [load]);

  const applyTpl = async () => {
    setBusy(true);
    setMsg(null);
    try {
      const res = await apiClient.applyDGCPPrepTemplate(opportunityId);
      setMsg(`Plantilla aplicada: +${res.created} (omitidos ${res.skipped_duplicates})`);
      await load();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Error");
    } finally {
      setBusy(false);
    }
  };

  const add = async () => {
    if (!title.trim()) return;
    setBusy(true);
    try {
      await apiClient.addDGCPPrepTask(opportunityId, {
        title: title.trim(),
        due_at: dueAt ? new Date(dueAt).toISOString() : undefined,
        priority: "medium",
      });
      setTitle("");
      setDueAt("");
      await load();
    } finally {
      setBusy(false);
    }
  };

  if (loading && !data) {
    return (
      <p className="flex items-center gap-2 text-sm text-slate-500">
        <Loader2 className="h-4 w-4 animate-spin" /> Preparación…
      </p>
    );
  }

  return (
    <div className="space-y-3 rounded-lg border p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h3 className="font-semibold text-slate-900">Preparación</h3>
          <p className="text-xs text-slate-500">
            Responsable: {data?.responsible_name || "Sin asignar"} · Deadline proceso:{" "}
            {formatDateTime(data?.process_deadline)}
          </p>
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => void applyTpl()} disabled={busy}>
            Aplicar checklist
          </Button>
          <Button size="sm" variant="outline" onClick={() => void load()}>
            Refrescar
          </Button>
        </div>
      </div>

      {data && (
        <>
          <div className="text-sm">
            Progreso: {data.progress.completed}/{data.progress.applicable} ({data.progress.pct}%)
            <div className="mt-1 h-2 max-w-xs rounded bg-slate-100">
              <div className="h-2 rounded bg-emerald-500" style={{ width: `${Math.min(100, data.progress.pct)}%` }} />
            </div>
          </div>
          {data.next_pending && (
            <p className="text-sm text-amber-900">
              Próximo: <strong>{data.next_pending.title}</strong> · {formatDateTime(data.next_pending.due_at)}
            </p>
          )}
        </>
      )}

      {msg && <p className="text-xs text-slate-600">{msg}</p>}

      <ul className="space-y-2">
        {(data?.items || []).map((t) => (
          <li key={t.id} className={cn("flex flex-wrap items-center gap-2 text-sm", t.status === "completed" && "opacity-60")}>
            <input
              type="checkbox"
              checked={t.status === "completed"}
              onChange={() => void apiClient.toggleDGCPPrepTask(t.id).then(load)}
            />
            <span className="min-w-[12rem] font-medium">{t.title}</span>
            <span className="text-xs text-slate-500">{t.assigned_user_name || "—"}</span>
            <span className="text-xs">
              {trafficDot(t.traffic_light)} {formatDateTime(t.due_at)}
            </span>
            <span className="text-xs capitalize text-slate-400">{t.priority}</span>
          </li>
        ))}
      </ul>

      <div className="flex flex-wrap items-end gap-2 border-t pt-3">
        <div className="min-w-[160px] flex-1">
          <label className="text-xs text-slate-500">Agregar pendiente</label>
          <input className="mt-1 w-full rounded border px-2 py-1.5 text-sm" value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div>
          <label className="text-xs text-slate-500">Deadline</label>
          <input
            type="datetime-local"
            className="mt-1 rounded border px-2 py-1.5 text-sm"
            value={dueAt}
            onChange={(e) => setDueAt(e.target.value)}
          />
        </div>
        <Button size="sm" onClick={() => void add()} disabled={busy || !title.trim()}>
          Agregar
        </Button>
      </div>
    </div>
  );
}
