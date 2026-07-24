"use client";

import { useCallback, useEffect, useState } from "react";

import { MotorGroupsView } from "@/components/lottery/control-center/groups-view";
import { MotorToolIntro } from "@/components/lottery/control-center/motor-tool-intro";
import type { GroupEntry } from "@/components/lottery/control-center/motor-types";
import { ApiError, apiClient } from "@/lib/api";

export default function GroupsTable1Page() {
  const [groups, setGroups] = useState<Record<string, GroupEntry>>({});
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await apiClient.getLotteryNumericRelationsGroups();
      setGroups((res.table1_groups || {}) as Record<string, GroupEntry>);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar agrupaciones T1");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-4">
      <MotorToolIntro
        title="Agrupaciones Tabla 1"
        description="Grupos de compañeros de Tabla 1. Solo consulta; no modifica el catálogo."
      />
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <MotorGroupsView groups={groups} table="table1" title="Agrupaciones Tabla 1" highlightCode={34} />
    </div>
  );
}
