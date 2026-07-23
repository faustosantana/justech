"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiClient } from "@/lib/api";

type LotOption = {
  id: string;
  name: string;
  slug?: string;
  country?: string | null;
  logo_url?: string | null;
  last_draw_date?: string | null;
  draw_count?: number;
  health_status?: string;
  is_sync_enabled?: boolean | null;
};

const SLOT_COUNT = 7;

export default function LotteryAIDefaultsPage() {
  const [catalog, setCatalog] = useState<LotOption[]>([]);
  const [slots, setSlots] = useState<(LotOption | null)[]>(Array(SLOT_COUNT).fill(null));
  const [queries, setQueries] = useState<string[]>(Array(SLOT_COUNT).fill(""));
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const [positionScope, setPositionScope] = useState<
    "first_position" | "any_position" | "ask_each_time"
  >("first_position");
  const [primaryPosition, setPrimaryPosition] = useState(1);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.getLotteryAIDefaults();
      const cat = ((res.catalog ?? []) as LotOption[]).filter((c) => c?.id);
      setCatalog(cat);
      const rawSlots = (res.slots ?? (res.defaults as { slots?: unknown[] })?.slots ?? []) as (
        | LotOption
        | null
        | undefined
      )[];
      const next = Array(SLOT_COUNT)
        .fill(null)
        .map((_, i) => (rawSlots[i] && (rawSlots[i] as LotOption).id ? (rawSlots[i] as LotOption) : null));
      setSlots(next);
      setQueries(next.map((s) => s?.name ?? ""));
      const defs = (res.defaults || {}) as {
        default_number_position_scope?: string;
        default_primary_position?: number;
      };
      const scope = defs.default_number_position_scope;
      if (scope === "any_position" || scope === "ask_each_time" || scope === "first_position") {
        setPositionScope(scope);
      } else if (scope === "specific_position") {
        setPositionScope("first_position");
      }
      if (typeof defs.default_primary_position === "number") {
        setPrimaryPosition(defs.default_primary_position);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar loterías predeterminadas");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const usedIds = useMemo(() => new Set(slots.filter(Boolean).map((s) => s!.id)), [slots]);

  const suggestions = (index: number) => {
    const q = (queries[index] || "").toLowerCase().trim();
    return catalog
      .filter((c) => !usedIds.has(c.id) || slots[index]?.id === c.id)
      .filter((c) => !q || c.name.toLowerCase().includes(q) || (c.slug || "").includes(q))
      .slice(0, 8);
  };

  const selectAt = (index: number, lot: LotOption | null) => {
    setSlots((prev) => {
      const next = [...prev];
      if (lot && next.some((s, i) => i !== index && s?.id === lot.id)) {
        setError("No se permiten loterías duplicadas");
        return prev;
      }
      next[index] = lot;
      return next;
    });
    setQueries((prev) => prev.map((q, i) => (i === index ? lot?.name ?? "" : q)));
    setError(null);
  };

  const move = (index: number, dir: -1 | 1) => {
    const j = index + dir;
    if (j < 0 || j >= SLOT_COUNT) return;
    setSlots((prev) => {
      const next = [...prev];
      [next[index], next[j]] = [next[j], next[index]];
      return next;
    });
    setQueries((prev) => {
      const next = [...prev];
      [next[index], next[j]] = [next[j], next[index]];
      return next;
    });
  };

  const save = async () => {
    setBusy(true);
    setMsg(null);
    try {
      await apiClient.putLotteryAIDefaults({
        slots: slots.map((s) => (s ? { id: s.id } : null)),
        default_analysis_lottery_ids: slots.filter(Boolean).map((s) => s!.id),
        user_may_override: true,
        default_number_position_scope: positionScope,
        default_primary_position: primaryPosition,
      });
      // Mirror into user/tenant Lottery preferences for chat runtime
      try {
        await apiClient.patchLotteryPreferences({
          default_number_position_scope: positionScope,
          default_primary_position: primaryPosition,
        });
      } catch {
        /* prefs endpoint may be unavailable for some roles */
      }
      setMsg("Loterías predeterminadas guardadas");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Loterías predeterminadas</h2>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading || busy}>
            Actualizar
          </Button>
          <Button size="sm" onClick={() => void save()} disabled={busy || loading}>
            Guardar
          </Button>
        </div>
      </div>

      <p className="text-sm text-muted-foreground">
        Seleccione hasta {SLOT_COUNT} loterías por nombre comercial. No se requieren UUID ni slugs.
        El slot 7 puede quedar pendiente.
      </p>

      {error && <p className="text-sm text-destructive">{error}</p>}
      {msg && <p className="text-sm text-muted-foreground">{msg}</p>}
      {loading && <p className="text-sm text-muted-foreground">Cargando…</p>}

      <Card>
        <CardHeader className="py-3">
          <CardTitle className="text-sm">Preferencias de Lottery IA</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <label className="block space-y-1">
            <span className="font-medium">Cuando pregunte por un número sin indicar posición</span>
            <select
              className="mt-1 w-full max-w-md rounded border bg-background px-2 py-1.5"
              value={positionScope}
              onChange={(e) =>
                setPositionScope(e.target.value as "first_position" | "any_position" | "ask_each_time")
              }
            >
              <option value="first_position">Buscar en primera posición</option>
              <option value="any_position">Buscar en cualquier posición</option>
              <option value="ask_each_time">Preguntarme cada vez</option>
            </select>
          </label>
          <label className="block space-y-1">
            <span className="text-muted-foreground">Posición primaria (1–3)</span>
            <Input
              type="number"
              min={1}
              max={3}
              className="max-w-[6rem]"
              value={primaryPosition}
              onChange={(e) => setPrimaryPosition(Number(e.target.value) || 1)}
            />
          </label>
          <p className="text-xs text-muted-foreground">
            Justech: valor recomendado «Buscar en primera posición». Solo se amplía a otras posiciones si el
            usuario lo pide o cambia esta preferencia.
          </p>
        </CardContent>
      </Card>

      <div className="space-y-3">
        {slots.map((slot, i) => (
          <Card key={i}>
            <CardHeader className="py-3">
              <CardTitle className="text-sm">Slot {i + 1}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex flex-wrap gap-2">
                <Input
                  placeholder="Buscar lotería…"
                  value={queries[i]}
                  onChange={(e) => setQueries((prev) => prev.map((q, idx) => (idx === i ? e.target.value : q)))}
                  className="max-w-sm"
                />
                <Button type="button" size="sm" variant="ghost" onClick={() => selectAt(i, null)}>
                  Limpiar
                </Button>
                <Button type="button" size="sm" variant="outline" onClick={() => move(i, -1)} disabled={i === 0}>
                  Subir
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => move(i, 1)}
                  disabled={i === SLOT_COUNT - 1}
                >
                  Bajar
                </Button>
              </div>
              {slot ? (
                <div className="rounded border border-border/60 p-2 text-sm">
                  <p className="font-medium">{slot.name}</p>
                  <p className="text-xs text-muted-foreground">
                    País: {slot.country ?? "—"} · Último: {slot.last_draw_date ?? "Sin datos suficientes"} ·
                    Sorteos: {slot.draw_count ?? "Sin datos suficientes"} · Salud:{" "}
                    {slot.health_status ?? "Sin datos suficientes"} · Sync:{" "}
                    {slot.is_sync_enabled == null ? "Sin datos suficientes" : slot.is_sync_enabled ? "on" : "off"}
                  </p>
                </div>
              ) : (
                <ul className="max-h-40 overflow-auto rounded border border-border/40 text-sm">
                  {suggestions(i).map((opt) => (
                    <li key={opt.id}>
                      <button
                        type="button"
                        className="block w-full px-3 py-1.5 text-left hover:bg-muted"
                        onClick={() => selectAt(i, opt)}
                      >
                        {opt.name}
                        <span className="ml-2 text-xs text-muted-foreground">{opt.country ?? ""}</span>
                      </button>
                    </li>
                  ))}
                  {suggestions(i).length === 0 && (
                    <li className="px-3 py-2 text-xs text-muted-foreground">Sin coincidencias en catálogo</li>
                  )}
                </ul>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
