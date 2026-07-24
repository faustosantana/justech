"use client";

import { useCallback, useEffect, useState } from "react";

import { MotorGroupsView } from "@/components/lottery/control-center/groups-view";
import type { GroupEntry } from "@/components/lottery/control-center/motor-types";
import { ApiError, apiClient } from "@/lib/api";

export default function GroupsTable2Page() {
  const [groups, setGroups] = useState<Record<string, GroupEntry>>({});
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await apiClient.getLotteryNumericRelationsGroups();
      setGroups((res.table2_groups || {}) as Record<string, GroupEntry>);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar agrupaciones T2");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">Agrupaciones · Tabla 2</h1>
      <p className="text-sm text-muted-foreground">Validación visual: código 53 → integrantes del grupo T2</p>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <MotorGroupsView groups={groups} table="table2" title="Agrupaciones Tabla 2" highlightCode={53} />
    </div>
  );
}
