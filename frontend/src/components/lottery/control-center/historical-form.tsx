"use client";

import { useEffect, useMemo, useState } from "react";

import type { LotOption } from "@/components/lottery/control-center/motor-types";
import { WINDOW_MODE_LABELS } from "@/components/lottery/control-center/nr-labels";
import { lotteryDisplayName } from "@/lib/lottery-display-names";
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

export const DEFAULT_HISTORY_FORM: HistoryFormState = {
  observed: "",
  dateFrom: "2015-01-01",
  dateTo: "",
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
};

function toggle(ids: string[], id: string): string[] {
  return ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id];
}

export function buildHistoryBody(form: HistoryFormState): Record<string, unknown> {
  const n = Number(form.observed);
  if (!Number.isInteger(n) || n < 1 || n > 100) {
    throw new Error("El número observado debe estar entre 1 y 100");
  }
  if (form.primaryIds.length < 1) {
    throw new Error("Selecciona al menos una lotería del universo activo");
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
}: Props) {
  const [form, setForm] = useState<HistoryFormState>(DEFAULT_HISTORY_FORM);
  const [localError, setLocalError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    if (!defaultSelectAll || !catalog.length) return;
    setForm((f) => {
      if (f.primaryIds.length) return f;
      const ids = catalog.map((c) => c.id);
      return { ...f, primaryIds: ids, confirmingIds: ids, followUpIds: ids };
    });
  }, [catalog, defaultSelectAll]);

  const primaryLabel = useMemo(() => {
    return form.primaryIds
      .map((id) => lotteryDisplayName(id, catalog.find((c) => c.id === id)?.name))
      .join(", ");
  }, [form.primaryIds, catalog]);

  const run = async () => {
    setLocalError(null);
    try {
      const body = buildHistoryBody(form);
      await onSubmit(body);
    } catch (e) {
      setLocalError(e instanceof Error ? e.message : "Error");
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <p className="text-sm text-muted-foreground">
          Por defecto analiza las siete loterías activas. Confirmación y seguimiento usan el mismo
          universo salvo que abra opciones avanzadas.
        </p>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="flex flex-wrap gap-3">
          <label>
            Número observado
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
            Horizonte posterior
            <Input
              className="mt-1 w-24"
              value={form.horizon}
              onChange={(e) => setForm((f) => ({ ...f, horizon: e.target.value }))}
            />
          </label>
        </div>

        <fieldset>
          <legend className="mb-1 font-medium">Ventana de confirmación</legend>
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
            <span className="font-medium">Loterías del universo activo</span>
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
            <div className="flex flex-wrap gap-3">
              <label>
                Candidato T1 (opcional)
                <Input
                  className="mt-1 w-24"
                  value={form.candidate}
                  onChange={(e) => setForm((f) => ({ ...f, candidate: e.target.value }))}
                />
              </label>
              <label>
                Confirmador T2 (opcional)
                <Input
                  className="mt-1 w-24"
                  value={form.confirmer}
                  onChange={(e) => setForm((f) => ({ ...f, confirmer: e.target.value }))}
                />
              </label>
              <label>
                Muestra mínima (opcional)
                <Input
                  className="mt-1 w-24"
                  value={form.minSample}
                  onChange={(e) => setForm((f) => ({ ...f, minSample: e.target.value }))}
                />
              </label>
            </div>

            <div>
              <div className="mb-1 font-medium">Loterías confirmadoras</div>
              <p className="mb-1 text-xs text-muted-foreground">
                Si no marca ninguna, se usan las del universo activo seleccionado arriba.
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
                Por defecto: mismo universo activo
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
        <Button type="button" disabled={busy} onClick={() => void run()}>
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
        n={String(rate.sample_size)} · {String(rate.sample_tier)}
      </div>
      {warn ? <div className="text-amber-700">{warn}</div> : null}
    </div>
  );
}
