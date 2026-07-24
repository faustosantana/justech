"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { MotorGroupsView } from "@/components/lottery/control-center/groups-view";
import { MotorToolIntro } from "@/components/lottery/control-center/motor-tool-intro";
import type { GroupEntry } from "@/components/lottery/control-center/motor-types";
import { Button } from "@/components/ui/button";
import { ApiError, apiClient } from "@/lib/api";

type Tab = "table1" | "table2";

export default function AgrupacionesPage() {
  const searchParams = useSearchParams();
  const initial: Tab = searchParams.get("tab") === "table2" ? "table2" : "table1";
  const [tab, setTab] = useState<Tab>(initial);
  const [t1, setT1] = useState<Record<string, GroupEntry>>({});
  const [t2, setT2] = useState<Record<string, GroupEntry>>({});
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await apiClient.getLotteryNumericRelationsGroups();
      setT1((res.table1_groups || {}) as Record<string, GroupEntry>);
      setT2((res.table2_groups || {}) as Record<string, GroupEntry>);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar agrupaciones");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-4">
      <MotorToolIntro
        title="Agrupaciones"
        description="Grupos de compañeros (Tabla 1) y confirmadores (Tabla 2) en una sola pantalla. Solo consulta; no modifica el catálogo."
      />
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant={tab === "table1" ? "default" : "outline"}
          size="sm"
          onClick={() => setTab("table1")}
        >
          Tabla 1
        </Button>
        <Button
          type="button"
          variant={tab === "table2" ? "default" : "outline"}
          size="sm"
          onClick={() => setTab("table2")}
        >
          Tabla 2
        </Button>
      </div>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      {tab === "table1" ? (
        <MotorGroupsView groups={t1} table="table1" title="Agrupaciones Tabla 1" highlightCode={34} />
      ) : (
        <MotorGroupsView groups={t2} table="table2" title="Agrupaciones Tabla 2" />
      )}
    </div>
  );
}
