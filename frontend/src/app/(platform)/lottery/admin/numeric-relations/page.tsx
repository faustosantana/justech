"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiClient } from "@/lib/api";
import { getAccessToken, getUserRole } from "@/lib/auth";
import { canAccessLotteryAdmin, isLotteryClientRole } from "@/lib/lottery";

type TableRow = {
  number: number;
  formula?: string;
  visible_value?: string;
  digits_without_point?: string;
  digit_count?: number;
  code?: number;
  group_numbers?: number[];
  group_label?: string;
};

type GroupEntry = { code: number; numbers: number[]; table: string };

type LotOption = { id: string; name: string; slug?: string };

type MatchRow = {
  companion?: number;
  neighbor?: number;
  lottery_name?: string;
  draw_date?: string;
  position?: number | string;
  points?: number;
  table2_code?: number;
  table2_group?: number[];
  neighbors?: number[];
  observed_number?: number;
  mother_code?: number;
  trace?: string;
};

type RankRow = {
  number: number;
  table1_code?: number;
  table2_code?: number;
  neighbors?: number[];
  matched_neighbors?: number[];
  score?: number;
  matches?: MatchRow[];
  trace?: string;
};

type TabId = "table1" | "table2" | "groups1" | "groups2" | "analysis";

const TABS: { id: TabId; label: string }[] = [
  { id: "table1", label: "Tabla 1" },
  { id: "table2", label: "Tabla 2" },
  { id: "groups1", label: "Agrupaciones T1" },
  { id: "groups2", label: "Agrupaciones T2" },
  { id: "analysis", label: "Análisis histórico" },
];

function NumberTable({ rows, title }: { rows: TableRow[]; title: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <p className="text-sm text-muted-foreground">
          Universo fijo 1–100. Esta vista no mezcla la otra tabla.
        </p>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left">
              <th className="py-2 pr-3">Número</th>
              <th className="py-2 pr-3">Fórmula</th>
              <th className="py-2 pr-3">Resultado visible</th>
              <th className="py-2 pr-3">Cadena dígitos</th>
              <th className="py-2 pr-3">Cant. dígitos</th>
              <th className="py-2 pr-3">Código</th>
              <th className="py-2">Grupo</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.number} className="border-b border-border/40 align-top">
                <td className="py-1.5 pr-3 font-medium">{r.number}</td>
                <td className="py-1.5 pr-3 font-mono text-xs">{r.formula}</td>
                <td className="py-1.5 pr-3 font-mono text-xs">{r.visible_value}</td>
                <td className="py-1.5 pr-3 font-mono text-xs break-all">{r.digits_without_point}</td>
                <td className="py-1.5 pr-3">{r.digit_count}</td>
                <td className="py-1.5 pr-3 font-semibold">{r.code}</td>
                <td className="py-1.5 text-xs">
                  <div className="font-medium">{r.group_label || `Código ${r.code}`}</div>
                  <div className="text-muted-foreground">
                    {(r.group_numbers || []).join(", ")}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function GroupsView({
  groups,
  title,
  tableLabel,
}: {
  groups: Record<string, GroupEntry>;
  title: string;
  tableLabel: string;
}) {
  const entries = useMemo(
    () => Object.values(groups || {}).sort((a, b) => a.code - b.code),
    [groups],
  );
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <p className="text-sm text-muted-foreground">
          Solo {tableLabel}. Ejemplo: Código X → números del grupo de {tableLabel}.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {entries.map((g) => (
          <div key={`${tableLabel}-${g.code}`} className="rounded-md border p-3">
            <div className="font-semibold">Código {g.code}</div>
            <div className="mt-1 text-sm text-muted-foreground">
              → números del grupo de {tableLabel}: {g.numbers.join(", ")}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function TraceExpand({ match }: { match: MatchRow }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded border p-2 text-xs">
      <button type="button" className="font-medium underline" onClick={() => setOpen((v) => !v)}>
        +{match.points ?? 1} punto — vecino {match.neighbor} (compañero {match.companion})
      </button>
      {open ? (
        <ol className="mt-2 list-decimal space-y-0.5 pl-4 text-muted-foreground">
          <li>número observado {match.observed_number}</li>
          <li>sorteo histórico real {match.draw_date}</li>
          <li>código madre {match.mother_code}</li>
          <li>compañero {match.companion}</li>
          <li>código Tabla 2 {match.table2_code}</li>
          <li>grupo Tabla 2 {(match.table2_group || []).join(", ")}</li>
          <li>vecino encontrado {match.neighbor}</li>
          <li>lotería {match.lottery_name}</li>
          <li>fecha {match.draw_date}</li>
          <li>posición {match.position}</li>
          <li>punto otorgado {match.points ?? 1}</li>
          {match.trace ? <li className="pt-1 italic">{match.trace}</li> : null}
        </ol>
      ) : null}
    </div>
  );
}

export default function LotteryNumericRelationsAdminPage() {
  const router = useRouter();
  const [tab, setTab] = useState<TabId>("table1");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [table1, setTable1] = useState<TableRow[]>([]);
  const [table2, setTable2] = useState<TableRow[]>([]);
  const [groups1, setGroups1] = useState<Record<string, GroupEntry>>({});
  const [groups2, setGroups2] = useState<Record<string, GroupEntry>>({});
  const [catalog, setCatalog] = useState<LotOption[]>([]);
  const [selectedLots, setSelectedLots] = useState<string[]>([]);
  const [observed, setObserved] = useState("26");
  const [occMode, setOccMode] = useState<"5" | "10" | "20" | "all">("10");
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [showJson, setShowJson] = useState(false);

  const load = useCallback(async () => {
    if (!getAccessToken()) {
      router.replace("/login?session=expired");
      return;
    }
    const role = getUserRole();
    if (isLotteryClientRole(role) || !canAccessLotteryAdmin(role)) {
      setError("Acceso denegado: se requiere permiso administrativo de loterías.");
      router.replace("/lottery");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [tables, groups, defaults] = await Promise.all([
        apiClient.getLotteryNumericRelationsTables(),
        apiClient.getLotteryNumericRelationsGroups(),
        apiClient.getLotteryAIDefaults().catch(() => ({ catalog: [] as LotOption[] })),
      ]);
      setTable1((tables.table1 || []) as TableRow[]);
      setTable2((tables.table2 || []) as TableRow[]);
      setGroups1((groups.table1_groups || {}) as Record<string, GroupEntry>);
      setGroups2((groups.table2_groups || {}) as Record<string, GroupEntry>);
      const cat = ((defaults as { catalog?: LotOption[] }).catalog || []).filter((c) => c?.id);
      setCatalog(cat);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar el motor");
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  const toggleLot = (id: string) => {
    setSelectedLots((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const runAnalysis = async () => {
    setAnalyzing(true);
    setError(null);
    setResult(null);
    try {
      const n = Number(observed);
      if (!Number.isInteger(n) || n < 1 || n > 100) {
        throw new Error("El número observado debe estar entre 1 y 100");
      }
      if (selectedLots.length < 1) {
        throw new Error("Selecciona al menos una lotería (no se inventan)");
      }
      const body =
        occMode === "all"
          ? {
              observed_number: n,
              lottery_ids: selectedLots,
              occurrence_mode: "all" as const,
              occurrence_k: null,
            }
          : {
              observed_number: n,
              lottery_ids: selectedLots,
              occurrence_mode: "last_k" as const,
              occurrence_k: Number(occMode),
            };
      const res = await apiClient.postLotteryNumericRelationsAnalyze(body);
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Análisis falló");
    } finally {
      setAnalyzing(false);
    }
  };

  const ranking = (result?.ranking || []) as RankRow[];
  const zeroScore = (result?.companions_score_zero || ranking.filter((r) => (r.score || 0) === 0)) as RankRow[];
  const hist = (result?.historical_occurrences || []) as Record<string, unknown>[];

  return (
    <AppShell>
      <div className="mx-auto flex max-w-6xl flex-col gap-4 p-4 md:p-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              Auditoría — Motor de Relaciones Numéricas
            </h1>
            <p className="text-sm text-muted-foreground">
              Una sola implementación del motor. Tabla 1 y Tabla 2 nunca se mezclan en la UI.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" asChild>
              <Link href="/lottery/admin/ai">Centro de IA</Link>
            </Button>
            <Button variant="outline" onClick={() => void load()}>
              Recargar
            </Button>
          </div>
        </div>

        {error ? (
          <div className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
            {error}
          </div>
        ) : null}

        <div className="flex flex-wrap gap-2">
          {TABS.map((t) => (
            <Button
              key={t.id}
              size="sm"
              variant={tab === t.id ? "default" : "outline"}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </Button>
          ))}
        </div>

        {loading ? (
          <p className="text-sm text-muted-foreground">Cargando tablas del motor…</p>
        ) : null}

        {!loading && tab === "table1" ? (
          <NumberTable rows={table1} title="Tabla 1 (madre) — 1÷1220 … 100÷1220" />
        ) : null}
        {!loading && tab === "table2" ? (
          <NumberTable rows={table2} title="Tabla 2 (confirmación) — 1220÷1 … 1220÷100" />
        ) : null}
        {!loading && tab === "groups1" ? (
          <GroupsView groups={groups1} title="Agrupaciones Tabla 1" tableLabel="Tabla 1" />
        ) : null}
        {!loading && tab === "groups2" ? (
          <GroupsView groups={groups2} title="Agrupaciones Tabla 2" tableLabel="Tabla 2" />
        ) : null}

        {!loading && tab === "analysis" ? (
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Parámetros del análisis</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Todos los valores son explícitos. No hay default oculto de ocurrencias.
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3 md:grid-cols-3">
                  <label className="block text-sm">
                    Número observado N (1–100)
                    <Input
                      className="mt-1"
                      value={observed}
                      onChange={(e) => setObserved(e.target.value)}
                      inputMode="numeric"
                    />
                  </label>
                  <div className="md:col-span-2">
                    <div className="text-sm font-medium">
                      Cantidad de últimas ocurrencias (seleccionado:{" "}
                      <span className="font-semibold text-foreground">
                        {occMode === "all" ? "todas" : occMode}
                      </span>
                      )
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {(["5", "10", "20", "all"] as const).map((k) => (
                        <Button
                          key={k}
                          size="sm"
                          variant={occMode === k ? "default" : "outline"}
                          onClick={() => setOccMode(k)}
                        >
                          {k === "all" ? "Todas" : `Últimas ${k}`}
                        </Button>
                      ))}
                    </div>
                  </div>
                </div>

                <div>
                  <div className="text-sm font-medium">
                    Loterías ({selectedLots.length} seleccionada(s))
                  </div>
                  <div className="mt-2 grid max-h-48 gap-1 overflow-y-auto rounded border p-2 md:grid-cols-2">
                    {catalog.length === 0 ? (
                      <p className="text-sm text-muted-foreground">
                        Sin catálogo de loterías predeterminadas. Configura defaults en el Centro de IA.
                      </p>
                    ) : (
                      catalog.map((lot) => (
                        <label key={lot.id} className="flex items-center gap-2 text-sm">
                          <input
                            type="checkbox"
                            checked={selectedLots.includes(lot.id)}
                            onChange={() => toggleLot(lot.id)}
                          />
                          {lot.name}
                        </label>
                      ))
                    )}
                  </div>
                </div>

                <Button disabled={analyzing} onClick={() => void runAnalysis()}>
                  {analyzing ? "Analizando…" : "Ejecutar análisis del motor"}
                </Button>
              </CardContent>
            </Card>

            {result ? (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Resultados del análisis</CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Motor: {(result.metadata as { engine?: string } | undefined)?.engine || "lottery.numeric_relations"}.
                    Señal histórica del método — no es certeza ni garantía.
                  </p>
                </CardHeader>
                <CardContent className="space-y-4 text-sm">
                  <div className="grid gap-2 md:grid-cols-2">
                    <div>Número observado: <strong>{String(result.observed_number)}</strong></div>
                    <div>Código madre: <strong>{String(result.mother_code)}</strong></div>
                    <div>
                      Loterías:{" "}
                      {((result.lottery_names as string[]) || []).join(", ") ||
                        ((result.lottery_ids as string[]) || []).join(", ")}
                    </div>
                    <div>
                      Ocurrencias usadas / encontradas:{" "}
                      <strong>
                        {String(result.occurrences_used)} / {String(result.occurrences_found)}
                      </strong>
                    </div>
                    <div>
                      Límite:{" "}
                      <strong>
                        {JSON.stringify(result.occurrence_limit)}
                      </strong>
                    </div>
                    <div>
                      Compañeros Tabla 1:{" "}
                      {((result.direct_companions as number[]) || []).join(", ")}
                    </div>
                  </div>

                  <div>
                    <div className="mb-1 font-medium">Fechas y sorteos utilizados (por draw_id)</div>
                    <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
                      {hist.map((h, i) => (
                        <li key={i}>
                          {String(h.lottery_name)} — {String(h.draw_date)}
                          {h.draw_time ? ` ${String(h.draw_time)}` : " (hora NULL)"} —{" "}
                          <span className="font-mono text-xs">draw_id={String(h.draw_id)}</span> — números{" "}
                          {((h.draw_numbers as { drawn_number: number }[]) || [])
                            .map((d) => d.drawn_number)
                            .join(", ")}
                        </li>
                      ))}
                      {hist.length === 0 ? <li>Ninguna ocurrencia histórica encontrada.</li> : null}
                    </ul>
                  </div>

                  <div className="rounded border p-3 text-xs text-muted-foreground">
                    <div className="mb-1 font-medium text-foreground">Metadata técnica (dedupe / sync)</div>
                    <div>
                      draw_ids analizados:{" "}
                      {String(
                        (result.metadata as Record<string, unknown> | undefined)
                          ?.draw_ids_analyzed_count ??
                          (result.analysis_metadata as Record<string, unknown> | undefined)
                            ?.draw_ids_analyzed_count ??
                          "—"
                      )}
                    </div>
                    <div>
                      descartados por dedupe interno:{" "}
                      {String(
                        (result.metadata as Record<string, unknown> | undefined)
                          ?.internal_dedupe_discarded_count ??
                          (result.analysis_metadata as Record<string, unknown> | undefined)
                            ?.internal_dedupe_discarded_count ??
                          "—"
                      )}
                    </div>
                    <div>
                      posibles duplicados por contenido (sync):{" "}
                      {String(
                        (result.metadata as Record<string, unknown> | undefined)
                          ?.possible_content_duplicate_draws_detected ??
                          (result.analysis_metadata as Record<string, unknown> | undefined)
                            ?.possible_content_duplicate_draws_detected ??
                          false
                      )}{" "}
                      — permanecen separados por draw_id distinto (sync no modificado).
                    </div>
                  </div>

                  <div>
                    <div className="mb-1 font-medium">Ranking completo (mayor → menor; incluye score 0)</div>
                    <ol className="space-y-3">
                      {ranking.map((c, idx) => (
                        <li key={c.number} className="rounded border p-3">
                          <div className="font-semibold">
                            {idx + 1}. Compañero {c.number} — score {c.score}
                          </div>
                          <div className="text-muted-foreground">
                            Código Tabla 2: {c.table2_code}. Vecinos: {(c.neighbors || []).join(", ")}.
                            Coincidencias: {(c.matched_neighbors || []).join(", ") || "ninguna"}.
                          </div>
                          <div className="mt-2 space-y-1">
                            {(c.matches || []).map((m, mi) => (
                              <TraceExpand key={mi} match={m} />
                            ))}
                          </div>
                        </li>
                      ))}
                    </ol>
                  </div>

                  <div>
                    <div className="mb-1 font-medium">Compañeros con puntuación 0 (no ocultos)</div>
                    <p>
                      {zeroScore.map((c) => c.number).join(", ") || "Ninguno"}
                    </p>
                  </div>

                  <div>
                    <Button size="sm" variant="outline" onClick={() => setShowJson((v) => !v)}>
                      {showJson ? "Ocultar JSON técnico" : "Mostrar JSON técnico (auditoría avanzada)"}
                    </Button>
                    {showJson ? (
                      <pre className="mt-2 max-h-96 overflow-auto rounded bg-muted p-3 text-xs">
                        {JSON.stringify(result, null, 2)}
                      </pre>
                    ) : null}
                  </div>
                </CardContent>
              </Card>
            ) : null}
          </div>
        ) : null}
      </div>
    </AppShell>
  );
}
