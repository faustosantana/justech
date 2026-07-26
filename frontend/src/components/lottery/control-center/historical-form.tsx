"use client";

import { useEffect, useMemo, useState } from "react";

import type { LotOption } from "@/components/lottery/control-center/motor-types";
import { WINDOW_MODE_LABELS } from "@/components/lottery/control-center/nr-labels";
import { lotteryDisplayName } from "@/lib/lottery-display-names";
import { apiClient } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export type HistoryFormState = {
  observed: string;
  dateFrom: string;
  dateTo: string;
  primaryIds: string[];
  confirmingIds: string[];
  followUpIds: string[];
  followDefaultSamePrimary: boolean;
  windowMode: string;
  hoursAfter: string;
  nextK: string;
  candidate: string;
  confirmer: string;
  minSample: string;
  horizon: string;
};

function todayIso(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export const DEFAULT_HISTORY_FORM: HistoryFormState = {
  observed: "",
  dateFrom: "2015-01-01",
  // Always default to "today" — never a fixed year cap (e.g. 2023).
  dateTo: todayIso(),
  primaryIds: [],
  confirmingIds: [],
  followUpIds: [],
  followDefaultSamePrimary: true,
  windowMode: "SAME_DRAW",
  hoursAfter: "24",
  nextK: "3",
  candidate: "",
  confirmer: "",
  minSample: "",
  horizon: "10",
};

const WINDOW_MODES = [
  "SAME_DRAW",
  "SAME_DATE",
  "SAME_SESSION",
  "HOURS_AFTER",
  "NEXT_DRAW_PER_CONFIRMING_LOTTERY",
  "NEXT_K_DRAWS",
] as const;

type Props = {
  catalog: LotOption[];
  title: string;
  submitLabel: string;
  onSubmit: (body: Record<string, unknown>) => Promise<void>;
  busy?: boolean;
  error?: string | null;
  extra?: React.ReactNode;
  /** Preselect all catalog ids once when form primaryIds still empty. */
  defaultSelectAll?: boolean;
  /** Show visible Tabla 1 companion selector and require it before submit. */
  requireCandidate?: boolean;
  /** Also require a confirmation number (Tabla 2 neighbor). */
  requireConfirmer?: boolean;
  initialObserved?: string;
  initialCandidate?: string;
  initialConfirmer?: string;
};

function toggle(ids: string[], id: string): string[] {
  return ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id];
}

function extractCompanions(detail: Record<string, unknown>, observed: number): number[] {
  const nested = (detail.detail || {}) as Record<string, unknown>;
  const raw =
    (nested.group_members as number[]) ||
    (detail.group_numbers as number[]) ||
    (detail.group_members as number[]) ||
    [];
  return (Array.isArray(raw) ? raw : [])
    .map((x) => Number(x))
    .filter((n) => Number.isInteger(n) && n >= 1 && n <= 100 && n !== observed);
}

export function buildHistoryBody(form: HistoryFormState): Record<string, unknown> {
  const n = Number(form.observed);
  if (!Number.isInteger(n) || n < 1 || n > 100) {
    throw new Error("El número a analizar debe estar entre 1 y 100");
  }
  if (form.primaryIds.length < 1) {
    throw new Error("Seleccione al menos una lotería incluida");
  }
  const confirming =
    form.confirmingIds.length > 0 ? form.confirmingIds : form.primaryIds;
  const followUp = form.followDefaultSamePrimary
    ? form.primaryIds
    : form.followUpIds.length > 0
      ? form.followUpIds
      : form.primaryIds;

  const window: Record<string, unknown> = {
    mode: form.windowMode,
    timezone: "America/Santo_Domingo",
  };
  if (form.windowMode === "HOURS_AFTER") window.hours_after = Number(form.hoursAfter) || 24;
  if (form.windowMode === "NEXT_K_DRAWS") window.next_k = Number(form.nextK) || 3;

  const body: Record<string, unknown> = {
    observed_number: n,
    scope: {
      primary_lottery_ids: form.primaryIds,
      confirming_lottery_ids: confirming,
      follow_up_lottery_ids: followUp,
    },
    confirmation_window: window,
    max_horizon: Number(form.horizon) || 10,
    include_pairs_triples: true,
  };
  if (form.dateFrom) body.date_from = form.dateFrom;
  if (form.dateTo) body.date_to = form.dateTo;
  if (form.candidate) body.candidate = Number(form.candidate);
  if (form.confirmer) body.confirmer = Number(form.confirmer);
  if (form.minSample !== "") body.min_sample = Number(form.minSample);
  return body;
}

export function HistoricalAnalyzerForm({
  catalog,
  title,
  submitLabel,
  onSubmit,
  busy,
  error,
  extra,
  defaultSelectAll = true,
  requireCandidate = false,
  requireConfirmer = false,
  initialObserved,
  initialCandidate,
  initialConfirmer,
}: Props) {
  const [form, setForm] = useState<HistoryFormState>(() => ({
    ...DEFAULT_HISTORY_FORM,
    observed: initialObserved || "",
    candidate: initialCandidate || "",
    confirmer: initialConfirmer || "",
  }));
  const [localError, setLocalError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [t1Options, setT1Options] = useState<number[]>([]);
  const [t2Options, setT2Options] = useState<number[]>([]);
  const [loadingCompanions, setLoadingCompanions] = useState(false);
  const [fieldHint, setFieldHint] = useState<string | null>(null);

  useEffect(() => {
    if (!defaultSelectAll || !catalog.length) return;
    setForm((f) => {
      if (f.primaryIds.length) return f;
      const ids = catalog.map((c) => c.id);
      return { ...f, primaryIds: ids, confirmingIds: ids, followUpIds: ids };
    });
  }, [catalog, defaultSelectAll]);

  useEffect(() => {
    if (initialObserved) {
      setForm((f) => ({ ...f, observed: initialObserved }));
    }
  }, [initialObserved]);

  useEffect(() => {
    if (initialCandidate) {
      setForm((f) => ({ ...f, candidate: initialCandidate }));
    }
  }, [initialCandidate]);

  useEffect(() => {
    if (initialConfirmer) {
      setForm((f) => ({ ...f, confirmer: initialConfirmer }));
    }
  }, [initialConfirmer]);

  useEffect(() => {
    if (!requireCandidate && !requireConfirmer) return;
    const n = Number(String(form.observed).replace(/\D/g, ""));
    if (!Number.isInteger(n) || n < 1 || n > 100) {
      setT1Options([]);
      setT2Options([]);
      return;
    }
    let cancelled = false;
    setLoadingCompanions(true);
    void (async () => {
      try {
        const [t1, t2] = await Promise.all([
          apiClient.getLotteryNumericRelationsNumber(n, "table1"),
          apiClient.getLotteryNumericRelationsNumber(n, "table2"),
        ]);
        if (cancelled) return;
        const companions = extractCompanions(t1, n);
        const neighbors = extractCompanions(t2, n);
        setT1Options(companions);
        setT2Options(neighbors);
        setForm((f) => {
          let candidate = f.candidate;
          let confirmer = f.confirmer;
          if (requireCandidate) {
            if (companions.length === 1) candidate = String(companions[0]);
            else if (candidate && !companions.includes(Number(candidate))) candidate = "";
            else if (initialCandidate && companions.includes(Number(initialCandidate))) {
              candidate = String(initialCandidate);
            }
          }
          if (requireConfirmer) {
            if (neighbors.length === 1) confirmer = String(neighbors[0]);
            else if (confirmer && !neighbors.includes(Number(confirmer))) confirmer = "";
            else if (initialConfirmer && neighbors.includes(Number(initialConfirmer))) {
              confirmer = String(initialConfirmer);
            }
          }
          return { ...f, candidate, confirmer };
        });
      } catch {
        if (!cancelled) {
          setT1Options([]);
          setT2Options([]);
        }
      } finally {
        if (!cancelled) setLoadingCompanions(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [
    form.observed,
    requireCandidate,
    requireConfirmer,
    initialCandidate,
    initialConfirmer,
  ]);

  const primaryLabel = useMemo(() => {
    return form.primaryIds
      .map((id) => lotteryDisplayName(id, catalog.find((c) => c.id === id)?.name))
      .join(", ");
  }, [form.primaryIds, catalog]);

  const canSubmit = useMemo(() => {
    const n = Number(form.observed);
    if (!Number.isInteger(n) || n < 1 || n > 100) return false;
    if (form.primaryIds.length < 1) return false;
    if (requireCandidate && !form.candidate) return false;
    if (requireConfirmer && !form.confirmer) return false;
    return true;
  }, [form, requireCandidate, requireConfirmer]);

  const run = async () => {
    setLocalError(null);
    setFieldHint(null);
    if (requireCandidate && !form.candidate) {
      setFieldHint("Seleccione un compañero de Tabla 1.");
      return;
    }
    if (requireConfirmer && !form.confirmer) {
      setFieldHint("Seleccione un número de confirmación.");
      return;
    }
    try {
      const body = buildHistoryBody(form);
      await onSubmit(body);
    } catch (e) {
      setLocalError(e instanceof Error ? e.message : "Error");
    }
  };

  return (
    <Card className="border-blue-100">
      <CardHeader>
        <CardTitle className="text-base text-blue-900">{title}</CardTitle>
        <p className="text-sm text-muted-foreground">
          Por defecto analiza las siete loterías activas. Confirmación y seguimiento usan el mismo
          universo salvo que abra opciones avanzadas.
        </p>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="flex flex-wrap gap-3">
          <label>
            Número a analizar
            <Input
              className="mt-1 w-28"
              value={form.observed}
              onChange={(e) => setForm((f) => ({ ...f, observed: e.target.value }))}
              placeholder="1–100"
            />
          </label>
          <label>
            Desde
            <Input
              className="mt-1 w-40"
              type="date"
              value={form.dateFrom}
              onChange={(e) => setForm((f) => ({ ...f, dateFrom: e.target.value }))}
            />
          </label>
          <label>
            Hasta
            <Input
              className="mt-1 w-40"
              type="date"
              value={form.dateTo}
              onChange={(e) => setForm((f) => ({ ...f, dateTo: e.target.value }))}
            />
          </label>
          <label>
            Sorteos posteriores a revisar
            <Input
              className="mt-1 w-24"
              value={form.horizon}
              onChange={(e) => setForm((f) => ({ ...f, horizon: e.target.value }))}
            />
          </label>
        </div>

        {requireCandidate ? (
          <div className="rounded-lg border border-sky-100 bg-sky-50/50 p-3">
            <label className="block font-medium text-blue-900">
              Candidato de Tabla 1 / Compañero de Tabla 1
              <select
                className="mt-1 w-full max-w-md rounded border bg-background px-2 py-2"
                value={form.candidate}
                onChange={(e) => {
                  setFieldHint(null);
                  setForm((f) => ({ ...f, candidate: e.target.value }));
                }}
                disabled={loadingCompanions || t1Options.length === 0}
              >
                <option value="">
                  {loadingCompanions
                    ? "Cargando compañeros…"
                    : t1Options.length
                      ? "Seleccione un compañero"
                      : "Escriba un número para ver compañeros"}
                </option>
                {t1Options.map((n) => (
                  <option key={n} value={String(n)}>
                    {String(n).padStart(2, "0")}
                  </option>
                ))}
              </select>
            </label>
            <p className="mt-2 text-xs text-slate-600">
              Seleccione uno de los compañeros de Tabla 1 para revisar cómo se comporta frente a
              Tabla 2 y al histórico.
            </p>
            {fieldHint && !form.candidate ? (
              <p className="mt-1 text-xs text-amber-700">{fieldHint}</p>
            ) : null}
          </div>
        ) : null}

        {requireConfirmer ? (
          <div className="rounded-lg border border-emerald-100 bg-emerald-50/40 p-3">
            <label className="block font-medium text-blue-900">
              Números de confirmación
              <select
                className="mt-1 w-full max-w-md rounded border bg-background px-2 py-2"
                value={form.confirmer}
                onChange={(e) => {
                  setFieldHint(null);
                  setForm((f) => ({ ...f, confirmer: e.target.value }));
                }}
                disabled={loadingCompanions || t2Options.length === 0}
              >
                <option value="">
                  {loadingCompanions
                    ? "Cargando confirmaciones…"
                    : t2Options.length
                      ? "Seleccione un número de confirmación"
                      : "Escriba un número para ver confirmaciones"}
                </option>
                {t2Options.map((n) => (
                  <option key={n} value={String(n)}>
                    {String(n).padStart(2, "0")}
                  </option>
                ))}
              </select>
            </label>
            {fieldHint && form.candidate && !form.confirmer ? (
              <p className="mt-1 text-xs text-amber-700">{fieldHint}</p>
            ) : null}
          </div>
        ) : null}

        <fieldset>
          <legend className="mb-1 font-medium">Momento de confirmación</legend>
          <select
            className="mt-1 w-full max-w-md rounded border bg-background px-2 py-2"
            value={form.windowMode}
            onChange={(e) => setForm((f) => ({ ...f, windowMode: e.target.value }))}
          >
            {WINDOW_MODES.map((m) => (
              <option key={m} value={m}>
                {WINDOW_MODE_LABELS[m] || m}
              </option>
            ))}
          </select>
          {form.windowMode === "HOURS_AFTER" ? (
            <label className="mt-2 block text-xs">
              Horas después
              <Input
                className="mt-1 w-24"
                value={form.hoursAfter}
                onChange={(e) => setForm((f) => ({ ...f, hoursAfter: e.target.value }))}
              />
            </label>
          ) : null}
          {form.windowMode === "NEXT_K_DRAWS" ? (
            <label className="mt-2 block text-xs">
              K sorteos
              <Input
                className="mt-1 w-24"
                value={form.nextK}
                onChange={(e) => setForm((f) => ({ ...f, nextK: e.target.value }))}
              />
            </label>
          ) : null}
        </fieldset>

        <div>
          <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
            <span className="font-medium">Loterías incluidas</span>
            <div className="flex gap-2 text-xs">
              <button
                type="button"
                className="underline"
                onClick={() => {
                  const ids = catalog.map((c) => c.id);
                  setForm((f) => ({
                    ...f,
                    primaryIds: ids,
                    confirmingIds: showAdvanced ? f.confirmingIds : ids,
                    followUpIds: showAdvanced ? f.followUpIds : ids,
                  }));
                }}
              >
                Todas
              </button>
              <button
                type="button"
                className="underline"
                onClick={() =>
                  setForm((f) => ({ ...f, primaryIds: [], confirmingIds: [], followUpIds: [] }))
                }
              >
                Ninguna
              </button>
            </div>
          </div>
          <div className="flex max-h-36 flex-wrap gap-2 overflow-y-auto rounded border p-2">
            {catalog.map((l) => (
              <label key={`p-${l.id}`} className="flex items-center gap-1 text-xs">
                <input
                  type="checkbox"
                  checked={form.primaryIds.includes(l.id)}
                  onChange={() => {
                    const next = toggle(form.primaryIds, l.id);
                    setForm((f) => ({
                      ...f,
                      primaryIds: next,
                      confirmingIds: showAdvanced ? f.confirmingIds : next,
                      followUpIds: showAdvanced ? f.followUpIds : next,
                    }));
                  }}
                />
                {lotteryDisplayName(l.id, l.name)}
              </label>
            ))}
          </div>
        </div>

        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setShowAdvanced((v) => !v)}
        >
          {showAdvanced ? "Ocultar opciones avanzadas" : "Opciones avanzadas"}
        </Button>

        {showAdvanced ? (
          <div className="space-y-3 rounded-lg border border-dashed p-3">
            {!requireCandidate ? (
              <label>
                Compañero de Tabla 1 (opcional)
                <Input
                  className="mt-1 w-24"
                  value={form.candidate}
                  onChange={(e) => setForm((f) => ({ ...f, candidate: e.target.value }))}
                />
              </label>
            ) : null}
            {!requireConfirmer ? (
              <label>
                Número de confirmación (opcional)
                <Input
                  className="mt-1 w-24"
                  value={form.confirmer}
                  onChange={(e) => setForm((f) => ({ ...f, confirmer: e.target.value }))}
                />
              </label>
            ) : null}
            <label>
              Muestra mínima (opcional)
              <Input
                className="mt-1 w-24"
                value={form.minSample}
                onChange={(e) => setForm((f) => ({ ...f, minSample: e.target.value }))}
              />
            </label>

            <div>
              <div className="mb-1 font-medium">Loterías de confirmación</div>
              <p className="mb-1 text-xs text-muted-foreground">
                Si no marca ninguna, se usan las loterías incluidas arriba.
              </p>
              <div className="flex max-h-28 flex-wrap gap-2 overflow-y-auto rounded border p-2">
                {catalog.map((l) => (
                  <label key={`c-${l.id}`} className="flex items-center gap-1 text-xs">
                    <input
                      type="checkbox"
                      checked={form.confirmingIds.includes(l.id)}
                      onChange={() =>
                        setForm((f) => ({ ...f, confirmingIds: toggle(f.confirmingIds, l.id) }))
                      }
                    />
                    {lotteryDisplayName(l.id, l.name)}
                  </label>
                ))}
              </div>
            </div>

            <div>
              <div className="mb-1 font-medium">Lotería de seguimiento</div>
              <label className="mb-2 flex items-center gap-2 text-xs">
                <input
                  type="checkbox"
                  checked={form.followDefaultSamePrimary}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, followDefaultSamePrimary: e.target.checked }))
                  }
                />
                Por defecto: mismas loterías incluidas
                {form.followDefaultSamePrimary && primaryLabel ? ` (${primaryLabel})` : ""}
              </label>
              {!form.followDefaultSamePrimary ? (
                <div className="flex max-h-28 flex-wrap gap-2 overflow-y-auto rounded border p-2">
                  {catalog.map((l) => (
                    <label key={`f-${l.id}`} className="flex items-center gap-1 text-xs">
                      <input
                        type="checkbox"
                        checked={form.followUpIds.includes(l.id)}
                        onChange={() =>
                          setForm((f) => ({ ...f, followUpIds: toggle(f.followUpIds, l.id) }))
                        }
                      />
                      {lotteryDisplayName(l.id, l.name)}
                    </label>
                  ))}
                </div>
              ) : null}
            </div>
          </div>
        ) : null}

        {extra}
        <Button
          type="button"
          className="bg-blue-600 hover:bg-blue-700"
          disabled={busy || !canSubmit}
          onClick={() => void run()}
        >
          {busy ? "Calculando…" : submitLabel}
        </Button>
        {localError || error ? (
          <p className="text-sm text-destructive">{localError || error}</p>
        ) : null}
      </CardContent>
    </Card>
  );
}

export function RateCell({ rate }: { rate: Record<string, unknown> | null | undefined }) {
  if (!rate) return <span className="text-muted-foreground">—</span>;
  const num = rate.numerator as number;
  const den = rate.denominator as number;
  const pct = rate.rate_percent;
  const warn = rate.sample_warning as string | undefined;
  return (
    <div className="text-xs">
      <div>
        {num}/{den}
        {pct != null ? ` (${pct}%)` : ""}
      </div>
      <div className="text-muted-foreground">
        Casos: {String(rate.sample_size)}
      </div>
      {warn ? <div className="text-amber-700">{warn}</div> : null}
    </div>
  );
}
