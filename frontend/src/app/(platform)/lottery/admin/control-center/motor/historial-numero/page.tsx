"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

import { PrimaryHistoricalCharts } from "@/components/lottery/control-center/historical-charts";
import type { LotOption } from "@/components/lottery/control-center/motor-types";
import { NR_EMPTY_COPY, NrEmptyState } from "@/components/lottery/control-center/nr-empty-states";
import { SignalCard } from "@/components/lottery/control-center/signal-card";
import { sortSignalsForDisplay } from "@/components/lottery/control-center/signal-order";
import { WhyStrengthenedPanel } from "@/components/lottery/control-center/why-strengthened-panel";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiClient } from "@/lib/api";

type ChartBar = { label: string; value: number; hint?: string };

function SecondaryBars({ title, items }: { title: string; items: ChartBar[] }) {
  const max = Math.max(1, ...items.map((i) => i.value));
  if (!items.length) {
    return <NrEmptyState title={title} body={NR_EMPTY_COPY.noHistory.body} />;
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2" role="img" aria-label={title}>
        {items.map((item) => (
          <div key={item.label} className="grid grid-cols-[7rem_1fr_4rem] items-center gap-2 text-sm">
            <span className="truncate" title={item.label}>
              {item.label}
            </span>
            <div className="h-3 rounded bg-muted" aria-hidden>
              <div
                className="h-3 rounded bg-primary/70"
                style={{ width: `${Math.max(item.value === 0 ? 0 : 4, (100 * item.value) / max)}%` }}
              />
            </div>
            <span className="text-right tabular-nums">{item.value}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function toggle(ids: string[], id: string): string[] {
  return ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id];
}

function FieldHelp({ children }: { children: React.ReactNode }) {
  return <p className="mt-1 text-xs text-muted-foreground">{children}</p>;
}

export default function HistorialNumeroPage() {
  const searchParams = useSearchParams();
  const bootNumber = searchParams.get("number") || "35";
  const bootAuto = searchParams.get("auto") === "1";
  const bootFeatured = searchParams.get("featured") === "1";
  const bootLotteryIds = (searchParams.get("lottery_ids") || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  const bootDrawId = searchParams.get("draw_id") || "";

  const [catalog, setCatalog] = useState<LotOption[]>([]);
  const [featuredIds, setFeaturedIds] = useState<string[]>([]);
  const [number, setNumber] = useState(bootNumber);
  const [numberB, setNumberB] = useState("40");
  const [dateFrom, setDateFrom] = useState("2015-01-01");
  const [dateTo, setDateTo] = useState("");
  const [appearedIn, setAppearedIn] = useState<string[]>([]);
  const [confirmIn, setConfirmIn] = useState<string[]>([]);
  const [followIn, setFollowIn] = useState<string[]>([]);
  const [windowMode, setWindowMode] = useState("SAME_DRAW");
  const [horizon, setHorizon] = useState("7");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfile] = useState<Record<string, unknown> | null>(null);
  const [occurrences, setOccurrences] = useState<Record<string, unknown> | null>(null);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [nextDraws, setNextDraws] = useState<Record<string, unknown> | null>(null);
  const [why, setWhy] = useState<Record<string, unknown> | null>(null);
  const [compare, setCompare] = useState<Record<string, unknown> | null>(null);
  const [showTech, setShowTech] = useState(false);
  const [showMethod, setShowMethod] = useState(!bootAuto);
  const [showFilters, setShowFilters] = useState(!bootAuto);
  const [condFilter, setCondFilter] = useState("all");
  const [page, setPage] = useState(1);
  const [playerStep, setPlayerStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [catalogReady, setCatalogReady] = useState(false);
  const autoStarted = useRef(false);
  const abortRef = useRef<AbortController | null>(null);
  const playTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    void (async () => {
      try {
        const [lots, featuredCat] = await Promise.all([
          apiClient.getLotteryNumericRelationsLotteries(),
          apiClient.getLotteryCatalog({ featured_only: true, page: 1, page_size: 12 }).catch(() => null),
        ]);
        const items = (lots.items || []).filter((c) => c?.id);
        setCatalog(items);
        const feat = (featuredCat?.items || []).map((c) => c.id).filter(Boolean);
        setFeaturedIds(feat);
        const preferred =
          bootLotteryIds.length > 0
            ? bootLotteryIds
            : bootFeatured && feat.length
              ? feat
              : items.map((c) => c.id);
        setAppearedIn(preferred);
        setConfirmIn(preferred);
        setFollowIn(preferred);
        setCatalogReady(true);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Error loterías");
        setCatalogReady(true);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const scopeBody = useMemo(() => {
    const primary = appearedIn.length ? appearedIn : catalog.map((c) => c.id);
    return {
      primary_lottery_ids: primary,
      confirming_lottery_ids: confirmIn.length ? confirmIn : primary,
      follow_up_lottery_ids: followIn.length ? followIn : primary,
    };
  }, [appearedIn, confirmIn, followIn, catalog]);

  const baseBody = useCallback(() => {
    const n = Number(number);
    if (!Number.isInteger(n) || n < 1 || n > 100) throw new Error("El número debe estar entre 1 y 100");
    if (!scopeBody.primary_lottery_ids.length) throw new Error("Seleccione al menos una lotería");
    const body: Record<string, unknown> = {
      number: n,
      scope: scopeBody,
      confirmation_window: { mode: windowMode, timezone: "America/Santo_Domingo" },
      max_horizon: Number(horizon) || 7,
    };
    if (dateFrom) body.date_from = dateFrom;
    if (dateTo) body.date_to = dateTo;
    return body;
  }, [number, scopeBody, windowMode, horizon, dateFrom, dateTo]);

  const loadOccurrences = useCallback(
    async (p: number, condition: string) => {
      const body = { ...baseBody(), page: p, page_size: 10, condition, order: "desc" };
      const res = await apiClient.postLotteryNrNumberOccurrences(body);
      setOccurrences(res);
      setPage(p);
    },
    [baseBody],
  );

  const analyze = useCallback(async () => {
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    setBusy(true);
    setError(null);
    setDetail(null);
    setNextDraws(null);
    setWhy(null);
    setCompare(null);
    try {
      const body = baseBody();
      const [prof] = await Promise.all([
        apiClient.postLotteryNrNumberProfile(body),
        loadOccurrences(1, condFilter),
      ]);
      setProfile(prof);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Error");
      setProfile(null);
    } finally {
      setBusy(false);
    }
  }, [baseBody, condFilter, loadOccurrences]);

  const openCase = useCallback(
    async (drawId: string) => {
      setBusy(true);
      setError(null);
      try {
        const body = { ...baseBody(), draw_id: drawId };
        const d = await apiClient.postLotteryNrNumberOccurrenceDetail(body);
        setDetail(d);
        const confirmed = ((d.verdict as Record<string, unknown>)?.confirmed_numbers || []) as number[];
        const tree = d.relation_tree as Record<string, unknown>;
        const branches = (tree?.candidatos || []) as Record<string, unknown>[];
        const confs: number[] = [];
        for (const b of branches) {
          for (const v of (b.confirmadores_encontrados || []) as number[]) confs.push(v);
        }
        const nxt = await apiClient.postLotteryNrNumberNextDraws({
          draw_id: drawId,
          follow_up_lottery_ids: scopeBody.follow_up_lottery_ids,
          count: Number(horizon) || 7,
          mode: "DRAWS",
          strengthened_candidates: confirmed,
          confirmer_watch: confs,
        });
        setNextDraws(nxt);
        setPlayerStep(0);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "No se pudo abrir el caso");
      } finally {
        setBusy(false);
      }
    },
    [baseBody, horizon, scopeBody.follow_up_lottery_ids],
  );

  useEffect(() => {
    if (!catalogReady || !bootAuto || autoStarted.current) return;
    if (!appearedIn.length) return;
    autoStarted.current = true;
    void (async () => {
      await analyze();
      if (bootDrawId) {
        await openCase(bootDrawId);
        return;
      }
      // Abrir de inmediato la aparición más reciente del alcance (expediente-first).
      try {
        const body = {
          ...baseBody(),
          page: 1,
          page_size: 1,
          condition: "all",
          order: "desc",
        };
        const res = await apiClient.postLotteryNrNumberOccurrences(body);
        const first = ((res.items || []) as Record<string, unknown>[])[0];
        if (first?.draw_id) await openCase(String(first.draw_id));
      } catch {
        /* perfil ya cargado; caso opcional */
      }
    })();
  }, [catalogReady, bootAuto, appearedIn.length, analyze, openCase, bootDrawId, baseBody]);

  const askWhy = useCallback(
    async (candidate: number) => {
      try {
        const body: Record<string, unknown> = {
          ...baseBody(),
          candidate,
          draw_id: (detail?.anchor as Record<string, unknown>)?.draw_id,
        };
        const res = await apiClient.postLotteryNrWhyStrengthened(body);
        setWhy(res.why as Record<string, unknown>);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Error explicación");
      }
    },
    [baseBody, detail],
  );

  const runCompare = useCallback(async () => {
    setBusy(true);
    try {
      const n = Number(number);
      const m = Number(numberB);
      if (!Number.isInteger(m) || m < 1 || m > 100) throw new Error("Número B inválido");
      const body = {
        number_a: n,
        number_b: m,
        scope: scopeBody,
        confirmation_window: { mode: windowMode, timezone: "America/Santo_Domingo" },
        max_horizon: Number(horizon) || 7,
        ...(dateFrom ? { date_from: dateFrom } : {}),
        ...(dateTo ? { date_to: dateTo } : {}),
      };
      const res = await apiClient.postLotteryNrNumbersCompare(body);
      setCompare(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : err instanceof Error ? err.message : "Error");
    } finally {
      setBusy(false);
    }
  }, [number, numberB, scopeBody, windowMode, horizon, dateFrom, dateTo]);

  useEffect(() => {
    if (!playing || !nextDraws) return;
    const steps = (nextDraws.reproductor || []) as unknown[];
    playTimer.current = setInterval(() => {
      setPlayerStep((s) => {
        if (s >= steps.length - 1) {
          setPlaying(false);
          return s;
        }
        return s + 1;
      });
    }, 1600);
    return () => {
      if (playTimer.current) clearInterval(playTimer.current);
    };
  }, [playing, nextDraws]);

  const header = (profile?.header || {}) as Record<string, unknown>;
  const cond = (profile?.condition_summary || {}) as Record<string, unknown>;
  const charts = (profile?.charts || {}) as Record<string, unknown>;
  const steps = (profile?.methodology_steps || []) as Record<string, unknown>[];
  const occItems = ((occurrences?.items || []) as Record<string, unknown>[]) || [];
  const displaySignals = useMemo(() => {
    const raw = ((charts.senales || []) as Record<string, unknown>[]).map((s) => ({
      number: Number(s.number),
      confirmation_count: Number(s.confirmation_count || 0),
      evaluable_cases: Number(s.evaluable_cases || 0),
      rate_within_3: s.rate_within_3 == null ? null : Number(s.rate_within_3),
      typical_cycle: s.typical_cycle == null ? null : Number(s.typical_cycle),
      evidence_level: String(s.evidence_level || header.nivel_evidencia || "Evidencia limitada"),
      activators_text: String(s.activators_text || "Activación histórica observada."),
      historical_rate_label: String(s.historical_rate_label || "Sin tasa agregada."),
      typical_cycle_label: String(s.typical_cycle_label || "Ciclo no calculado."),
    }));
    return sortSignalsForDisplay(raw);
  }, [charts.senales, header.nivel_evidencia]);

  const signalHref = useCallback(
    (n: number) => {
      const q = new URLSearchParams();
      q.set("number", String(n));
      q.set("auto", "1");
      if (bootFeatured) q.set("featured", "1");
      if (appearedIn.length) q.set("lottery_ids", appearedIn.join(","));
      if (dateFrom) q.set("date_from", dateFrom);
      if (dateTo) q.set("date_to", dateTo);
      return `/lottery/admin/control-center/motor/historial-numero?${q.toString()}`;
    },
    [appearedIn, bootFeatured, dateFrom, dateTo],
  );

  const sampleWarning =
    profile && Number(profile.sample_size || 0) > 0 && Number(profile.sample_size || 0) < 10
      ? NR_EMPTY_COPY.smallSample(Number(profile.sample_size)).body
      : null;
  const tree = (detail?.relation_tree || {}) as Record<string, unknown>;
  const branches = (tree.candidatos || []) as Record<string, unknown>[];
  const verdict = (detail?.verdict || {}) as Record<string, unknown>;
  const player = ((nextDraws?.reproductor || []) as Record<string, unknown>[]) || [];
  const nextSteps = ((nextDraws?.steps || []) as Record<string, unknown>[]) || [];

  const LotChecks = ({
    value,
    onChange,
    label,
    help,
  }: {
    value: string[];
    onChange: (v: string[]) => void;
    label: string;
    help: string;
  }) => (
    <div>
      <div className="mb-1 font-medium">{label}</div>
      <div className="flex flex-wrap gap-2">
        {catalog
          .filter((lot) => !featuredIds.length || appearedIn.length === 0 || featuredIds.includes(lot.id) || value.includes(lot.id) || !bootFeatured)
          .map((lot) => (
          <label key={lot.id} className="flex items-center gap-1 rounded border px-2 py-1 text-sm">
            <input
              type="checkbox"
              checked={value.includes(lot.id)}
              onChange={() => onChange(toggle(value, lot.id))}
            />
            {lot.name}
          </label>
        ))}
      </div>
      <FieldHelp>{help}</FieldHelp>
    </div>
  );

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">HISTORIAL DEL NÚMERO</h1>
          <p className="max-w-3xl text-sm text-muted-foreground">
            Conozca todas las veces que salió un número, cómo actuaron sus relaciones matemáticas y qué
            sucedió después.
          </p>
        </div>
        <Button variant="outline" className="min-h-11" onClick={() => setShowFilters((v) => !v)}>
          {showFilters ? "Ocultar filtros" : "Cambiar búsqueda"}
        </Button>
      </header>

      {showFilters ? (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Buscar número</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <label>
              Número a investigar
              <Input className="mt-1" value={number} onChange={(e) => setNumber(e.target.value)} inputMode="numeric" />
              <FieldHelp>Escriba el número cuya historia desea conocer (1 a 100).</FieldHelp>
            </label>
            <label>
              Desde
              <Input className="mt-1" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
              <FieldHelp>Fecha inicial del período a revisar.</FieldHelp>
            </label>
            <label>
              Hasta
              <Input className="mt-1" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
              <FieldHelp>Deje vacío para llegar hasta el último sorteo disponible.</FieldHelp>
            </label>
            <label>
              Cantidad de sorteos posteriores
              <Input className="mt-1" value={horizon} onChange={(e) => setHorizon(e.target.value)} />
              <FieldHelp>Valor predeterminado: 7 sorteos reales (no son necesariamente 7 días).</FieldHelp>
            </label>
          </div>

          <LotChecks
            label="Lotería donde apareció"
            value={appearedIn}
            onChange={setAppearedIn}
            help="Elija una, varias o todas las loterías donde buscar apariciones del número."
          />
          <LotChecks
            label="Loterías donde buscar confirmaciones"
            value={confirmIn}
            onChange={setConfirmIn}
            help="Aquí buscaremos los números de Tabla 2 que puedan fortalecer a los compañeros de Tabla 1."
          />
          <LotChecks
            label="Lotería donde comprobar qué ocurrió después"
            value={followIn}
            onChange={setFollowIn}
            help="Aquí revisaremos si el número fortalecido apareció posteriormente."
          />

          <label className="block max-w-sm">
            Ventana de confirmación
            <select
              className="mt-1 w-full rounded border bg-background px-2 py-2"
              value={windowMode}
              onChange={(e) => setWindowMode(e.target.value)}
            >
              <option value="SAME_DRAW">Mismo sorteo</option>
              <option value="SAME_DATE">Misma fecha</option>
              <option value="HOURS_AFTER">Horas después</option>
              <option value="NEXT_K_DRAWS">Próximos sorteos</option>
            </select>
            <FieldHelp>Define en qué momento se buscan los confirmadores de Tabla 2.</FieldHelp>
          </label>

          <div className="flex flex-wrap gap-2">
            <Button className="min-h-11 min-w-[10rem]" onClick={() => void analyze()} disabled={busy}>
              {busy ? "Analizando…" : "Analizar número"}
            </Button>
            <Button
              variant="outline"
              className="min-h-11"
              onClick={() => {
                setNumber("");
                setDateFrom("");
                setDateTo("");
                setProfile(null);
                setOccurrences(null);
                setDetail(null);
              }}
            >
              Limpiar
            </Button>
            <Button
              variant="outline"
              className="min-h-11"
              onClick={() => {
                setDateFrom("2015-01-01");
                setDateTo("");
                if (catalog.length) {
                  const all = catalog.map((c) => c.id);
                  setAppearedIn(all);
                  setConfirmIn(all);
                  setFollowIn(all);
                }
              }}
            >
              Usar todo el histórico
            </Button>
            <Button
              variant="outline"
              className="min-h-11"
              disabled={!featuredIds.length}
              onClick={() => {
                setAppearedIn(featuredIds);
                setConfirmIn(featuredIds);
                setFollowIn(featuredIds);
              }}
            >
              Solo las 7 destacadas
            </Button>
            <Button variant="ghost" className="min-h-11" onClick={() => setShowMethod((v) => !v)}>
              Ver metodología
            </Button>
          </div>
          {error ? (
            <NrEmptyState title={NR_EMPTY_COPY.serviceError.title} body={error} />
          ) : null}
        </CardContent>
      </Card>
      ) : (
        <div className="rounded-md border bg-muted/30 px-3 py-2 text-sm">
          Investigando el <strong>{number}</strong>
          {busy ? "…" : profile ? " — expediente listo." : "."}{" "}
          <button type="button" className="text-primary underline" onClick={() => setShowFilters(true)}>
            Ajustar búsqueda
          </button>
          {error ? <span className="ml-2 text-destructive">{error}</span> : null}
        </div>
      )}

      {showMethod ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Metodología en cinco pasos</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-5">
            {(steps.length
              ? steps
              : [
                  { paso: 1, titulo: "Salió el número", texto: "Se registra la aparición." },
                  { paso: 2, titulo: "Tabla 1 encuentra compañeros", texto: "Candidatos." },
                  { paso: 3, titulo: "Tabla 2 busca confirmadores", texto: "Vecinos." },
                  { paso: 4, titulo: "Se fortalece el compañero", texto: "La fuerza va al candidato." },
                  { paso: 5, titulo: "Se revisa qué pasó después", texto: "Sorteos posteriores." },
                ]
            ).map((s) => (
              <div key={String(s.paso)} className="rounded-lg border p-3">
                <div className="text-xs font-semibold uppercase text-muted-foreground">Paso {String(s.paso)}</div>
                <div className="mt-1 font-medium">{String(s.titulo)}</div>
                <p className="mt-1 text-sm text-muted-foreground">{String(s.texto)}</p>
              </div>
            ))}
            <p className="md:col-span-5 rounded border border-amber-200 bg-amber-50 p-3 text-sm dark:bg-amber-950/30">
              El confirmador aporta la evidencia. La fuerza la recibe el compañero de Tabla 1 al cual
              pertenece.
            </p>
          </CardContent>
        </Card>
      ) : null}

      {profile ? (
        <>
          <section aria-label="Encabezado del expediente" className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <Card className="sm:col-span-2 lg:col-span-3">
              <CardContent className="pt-6">
                <h2 className="text-xl font-semibold">{String(header.titulo || "")}</h2>
              </CardContent>
            </Card>
            {[
              { label: "Apareció", value: `${header.aparecio ?? "—"} veces` },
              { label: "Primera aparición", value: String(header.primera_aparicion ?? "—") },
              { label: "Última aparición", value: String(header.ultima_aparicion ?? "—") },
              { label: "Loterías donde ha salido", value: String(header.loterias_donde_ha_salido ?? "—") },
              { label: "Período analizado", value: String(header.periodo ?? "—") },
              { label: "Nivel de evidencia", value: String(header.nivel_evidencia ?? "—") },
            ].map((c) => (
              <Card key={c.label}>
                <CardContent className="space-y-1 pt-6">
                  <div className="text-xs uppercase tracking-wide text-muted-foreground">{c.label}</div>
                  <div className="text-2xl font-semibold leading-tight">{c.value}</div>
                </CardContent>
              </Card>
            ))}
          </section>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Respuesta principal</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div>
                <strong>CONDICIONES POSITIVAS:</strong> {String(cond.positivas)} de{" "}
                {String(cond.total_apariciones)} apariciones.
              </div>
              <div>
                <strong>CONDICIONES PARCIALES:</strong> {String(cond.parciales)} de{" "}
                {String(cond.total_apariciones)}.
              </div>
              <div>
                <strong>CONDICIONES NEGATIVAS:</strong> {String(cond.negativas)} de{" "}
                {String(cond.total_apariciones)}.
              </div>
              <div>
                <strong>PORCENTAJE OBSERVADO:</strong>{" "}
                {cond.porcentaje_observado != null ? `${cond.porcentaje_observado} %` : "—"}
              </div>
              <p className="text-muted-foreground">{String(cond.texto || "")}</p>
              <p className="text-xs text-muted-foreground">{String(cond.disclaimer || "")}</p>
            </CardContent>
          </Card>

          <section className="space-y-3" aria-label="Señales y predicciones">
            <div>
              <h2 className="text-lg font-semibold">Señales y predicciones</h2>
              <p className="text-sm text-muted-foreground">
                Orden de visualización (no es fuerza matemática oficial): más confirmaciones, mayor
                muestra evaluable, mejor respuesta en 3 sorteos, ciclo más corto, número ascendente.
              </p>
            </div>
            {displaySignals.length ? (
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {displaySignals.map((s) => (
                  <SignalCard
                    key={s.number}
                    number={s.number}
                    evidenceLevel={s.evidence_level}
                    confirmationCount={s.confirmation_count}
                    activatorsText={s.activators_text}
                    historicalRateLabel={s.historical_rate_label}
                    typicalCycleLabel={s.typical_cycle_label}
                    analysisHref={signalHref(s.number)}
                  />
                ))}
              </div>
            ) : (
              <NrEmptyState {...NR_EMPTY_COPY.noSignals} />
            )}
          </section>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Resumen automático</CardTitle>
            </CardHeader>
            <CardContent className="whitespace-pre-line text-sm leading-relaxed">
              {String(profile.resumen_automatico || "")}
            </CardContent>
          </Card>

      {detail ? (
        <section className="space-y-4" aria-label="Expediente de aparición">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Expediente de esta aparición</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="text-lg font-semibold">{String(verdict.headline)}</div>
              <p>{String(verdict.reason)}</p>
              <p className="text-muted-foreground">{String(detail.natural_line || "")}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Árbol visual de relaciones</CardTitle>
            </CardHeader>
            <CardContent className="font-mono text-sm">
              <div className="font-sans text-base font-semibold">{String(tree.numero_que_salio)}</div>
              <ul className="mt-2 space-y-2 font-sans">
                {branches.map((b) => (
                  <li key={String(b.candidato)} className="rounded border p-2">
                    <button type="button" className="font-medium underline-offset-2 hover:underline" onClick={() => void askWhy(Number(b.candidato))}>
                      ├── {String(b.candidato)} · {String(b.estado)} · fuerza {String(b.fuerza)} ·{" "}
                      {String(b.confirmaciones)} confirmaciones
                    </button>
                    <ul className="ml-4 mt-1 space-y-1 text-muted-foreground">
                      {((b.vecinos_tabla2 || []) as Record<string, unknown>[]).length === 0 ? (
                        <li>└── Sin vecinos Tabla 2</li>
                      ) : (
                        ((b.vecinos_tabla2 || []) as Record<string, unknown>[]).map((v) => (
                          <li key={String(v.numero)}>
                            ├── {String(v.numero)} {String(v.etiqueta)}
                          </li>
                        ))
                      )}
                    </ul>
                  </li>
                ))}
              </ul>
              <p className="mt-3 font-sans text-xs text-muted-foreground">{String(tree.aclaracion || "")}</p>
            </CardContent>
          </Card>

          <div className="grid gap-3 md:grid-cols-2">
            {branches.map((b) => (
              <Card key={`card-${String(b.candidato)}`}>
                <CardHeader>
                  <CardTitle className="text-base">NÚMERO {String(b.candidato)}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-1 text-sm">
                  {Number(b.confirmaciones) > 0 ? (
                    <>
                      <div>Confirmaciones actuales: {String(b.confirmaciones)}</div>
                      <div>
                        Confirmado por:{" "}
                        {((b.confirmadores_encontrados || []) as number[]).join(", ") || "—"}
                      </div>
                    </>
                  ) : (
                    <p>No recibió confirmaciones en esta ocasión.</p>
                  )}
                  <Button className="mt-2" size="sm" onClick={() => void askWhy(Number(b.candidato))}>
                    ¿Por qué se fortaleció?
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>

          {why ? <WhyStrengthenedPanel why={why} /> : null}

          {nextDraws ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  {String(nextDraws.mode_label || "Próximos siete sorteos")}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <p className="text-muted-foreground">
                  Secuencia por sorteos reales (draw_id). Distinto de «siete días calendario».
                </p>
                {nextDraws.censored ? (
                  <p className="rounded border border-amber-200 bg-amber-50 p-2 dark:bg-amber-950/30">
                    {String(nextDraws.censored_texto)}
                  </p>
                ) : null}
                <div className="grid gap-2 md:grid-cols-2">
                  {nextSteps.map((s) => (
                    <div key={String(s.posicion)} className="rounded border p-3">
                      <div className="font-semibold">{String(s.etiqueta)}</div>
                      <div>
                        {String(s.fecha_texto)} — {String(s.loteria)}
                      </div>
                      <p className="mt-1">{String(s.texto)}</p>
                    </div>
                  ))}
                </div>
                {nextDraws.first_response_offset != null ? (
                  <p className="font-medium">
                    Respuesta observada: {String(nextDraws.first_response_offset)} sorteos.
                  </p>
                ) : null}

                <div className="rounded-lg border p-3">
                  <div className="mb-2 font-medium">Reproducir el caso</div>
                  <p className="min-h-[3rem]">
                    Paso {playerStep + 1}: {String(player[playerStep]?.titulo || "—")}
                    {player[playerStep]?.texto ? ` — ${String(player[playerStep].texto)}` : ""}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Button size="sm" variant="outline" onClick={() => setPlayerStep((s) => Math.max(0, s - 1))}>
                      Anterior
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setPlayerStep((s) => Math.min(player.length - 1, s + 1))}
                    >
                      Siguiente
                    </Button>
                    <Button size="sm" onClick={() => setPlaying(true)}>
                      Reproducir
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => setPlaying(false)}>
                      Pausar
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        setPlaying(false);
                        setPlayerStep(0);
                      }}
                    >
                      Reiniciar
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ) : null}
        </section>
      ) : null}

          <PrimaryHistoricalCharts
            number={number}
            header={header}
            charts={charts}
            condition={cond}
            sampleWarning={sampleWarning}
          />

          <details className="rounded border p-3">
            <summary className="cursor-pointer text-sm font-medium">
              Más contexto (confirmadores y calendario)
            </summary>
            <div className="mt-3 grid gap-4 lg:grid-cols-2">
              <SecondaryBars
                title="Números que confirmaron más veces"
                items={((charts.confirmadores || []) as Record<string, unknown>[]).map((r) => ({
                  label: `Nº ${r.confirmador}`,
                  value: Number(r.veces || 0),
                }))}
              />
              <SecondaryBars
                title="Comportamiento por mes"
                items={((charts.por_mes || []) as Record<string, unknown>[]).map((r) => ({
                  label: String(r.mes),
                  value: Number(r.cantidad || 0),
                }))}
              />
              <SecondaryBars
                title="Comportamiento por día de la semana"
                items={((charts.por_dia_semana || []) as Record<string, unknown>[]).map((r) => ({
                  label: String(r.dia),
                  value: Number(r.cantidad || 0),
                }))}
              />
            </div>
          </details>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">TODAS LAS APARICIONES</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex flex-wrap gap-2">
                {[
                  ["all", "Todas"],
                  ["positive", "Condición positiva"],
                  ["partial", "Parcial"],
                  ["negative", "Negativa"],
                ].map(([k, lab]) => (
                  <Button
                    key={k}
                    size="sm"
                    variant={condFilter === k ? "default" : "outline"}
                    onClick={() => {
                      setCondFilter(k);
                      void loadOccurrences(1, k);
                    }}
                  >
                    {lab}
                  </Button>
                ))}
              </div>
              <p className="text-sm text-muted-foreground">
                Total filtrado: {String(occurrences?.total ?? "—")}
              </p>
              <ul className="space-y-3">
                {occItems.map((item) => (
                  <li key={String(item.draw_id)} className="rounded-lg border p-3 text-sm">
                    <div className="font-medium">
                      {String(item.fecha_texto)} — {String(item.loteria)}
                    </div>
                    <p className="mt-1 text-muted-foreground">{String(item.texto)}</p>
                    <div className="mt-2 font-semibold">{String(item.estado)}</div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <Button size="sm" onClick={() => void openCase(String(item.draw_id))}>
                        Ver caso
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => void openCase(String(item.draw_id))}>
                        Ver siete sorteos posteriores
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  disabled={page <= 1}
                  onClick={() => void loadOccurrences(page - 1, condFilter)}
                >
                  Anterior
                </Button>
                <Button
                  variant="outline"
                  disabled={page * 10 >= Number(occurrences?.total || 0)}
                  onClick={() => void loadOccurrences(page + 1, condFilter)}
                >
                  Siguiente
                </Button>
              </div>
            </CardContent>
          </Card>
        </>
      ) : null}



      <Card>
        <CardHeader>
          <CardTitle className="text-base">Comparador de números</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="flex flex-wrap items-end gap-3">
            <label>
              Número A
              <Input className="mt-1 w-24" value={number} onChange={(e) => setNumber(e.target.value)} />
            </label>
            <span className="pb-2">vs.</span>
            <label>
              Número B
              <Input className="mt-1 w-24" value={numberB} onChange={(e) => setNumberB(e.target.value)} />
            </label>
            <Button onClick={() => void runCompare()} disabled={busy}>
              Comparar
            </Button>
          </div>
          {compare ? (
            <div className="space-y-2">
              <ul className="list-disc pl-5">
                {((compare.conclusiones || []) as string[]).map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <details className="rounded border p-3 text-sm" open={showTech} onToggle={(e) => setShowTech((e.target as HTMLDetailsElement).open)}>
        <summary className="cursor-pointer font-medium">Ver evidencia técnica</summary>
        <pre className="mt-2 max-h-80 overflow-auto rounded bg-muted p-2 text-xs">
          {JSON.stringify(
            {
              methodology_version: profile?.methodology_version,
              trace_id: profile?.trace_id,
              effective_parameters: profile?.effective_parameters,
              sample_size: profile?.sample_size,
              evaluable_events: profile?.evaluable_events,
              censored_events: profile?.censored_events,
              detail_anchor: detail?.anchor,
              next_draws_mode: nextDraws?.mode,
            },
            null,
            2,
          )}
        </pre>
      </details>
    </div>
  );
}
