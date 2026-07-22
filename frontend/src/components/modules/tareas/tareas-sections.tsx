"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  Briefcase,
  ClipboardList,
  RefreshCw,
} from "lucide-react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { t } from "@/i18n";
import { apiClient } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import { PRIORITY_LABELS, priorityClass, type Task, type WorkHub } from "@/lib/tasks";
import { cn } from "@/lib/utils";

const m = t();

function TaskList({ items, empty }: { items: Task[]; empty: string }) {
  if (!items.length) return <p className="text-sm text-muted-foreground">{empty}</p>;
  return (
    <div className="space-y-2">
      {items.slice(0, 12).map((task) => (
        <Link
          key={task.id}
          href={`/tasks/${task.id}`}
          className="flex items-center justify-between rounded-lg border p-3 hover:bg-muted/30"
        >
          <div>
            <p className="text-sm font-medium">{task.title}</p>
            <p className="text-xs text-muted-foreground">
              {task.due_date ?? m.common.none}
              {task.assigned_to_name && ` · ${task.assigned_to_name}`}
            </p>
          </div>
          <span className={cn("rounded-full px-2 py-0.5 text-xs", priorityClass(task.priority))}>
            {PRIORITY_LABELS[task.priority]}
          </span>
        </Link>
      ))}
    </div>
  );
}

export function TareasListSection({ sectionId }: { sectionId: string }) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const params: Record<string, string | number> = { limit: 80 };
    if (sectionId === "vencidas") params.overdue = "true";
    if (sectionId === "hoy") params.due_today = "true";
    if (sectionId === "equipo") params.scope = "team";
    apiClient
      .getTasks(params)
      .then((r) => setTasks(r.items))
      .finally(() => setLoading(false));
  }, [sectionId]);

  if (loading) return <p className="text-sm text-muted-foreground">Cargando tareas…</p>;
  return <TaskList items={tasks} empty="Sin tareas en esta vista." />;
}

export function TareasWorkHubSection() {
  const router = useRouter();
  const [hub, setHub] = useState<WorkHub | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!getAccessToken()) {
      router.replace("/login");
      return;
    }
    setLoading(true);
    try {
      setHub(await apiClient.getWorkHub());
    } finally {
      setLoading(false);
    }
  }, [router]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading || !hub) return <p className="text-sm text-muted-foreground">{m.common.loading}</p>;

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          <RefreshCw className={cn("mr-2 h-4 w-4", loading && "animate-spin")} />
          {m.common.refresh}
        </Button>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {[
          { label: m.work.pending, value: hub.my_pending, color: "text-amber-400" },
          { label: m.work.inProgress, value: hub.my_in_progress, color: "text-blue-400" },
          { label: m.work.overdue, value: hub.my_overdue, color: "text-red-400" },
          { label: m.work.critical, value: hub.my_critical, color: "text-red-500" },
          { label: m.work.dueSoon, value: hub.my_due_soon, color: "text-sky-400" },
        ].map((kpi) => (
          <Card key={kpi.label}>
            <CardContent className="pt-6">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">{kpi.label}</p>
              <p className={cn("text-3xl font-bold", kpi.color)}>{kpi.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>
      {hub.alerts.length > 0 && (
        <Card className="border-amber-500/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertTriangle className="h-4 w-4 text-amber-400" />
              {m.work.operationalAlerts}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {hub.alerts.map((a) => (
              <div key={a.type} className="flex items-center justify-between rounded-lg border p-3">
                <div>
                  <p className="text-sm font-medium">{a.title}</p>
                  <p className="text-xs text-muted-foreground">{a.message}</p>
                </div>
                {a.link && (
                  <Link href={a.link}>
                    <Button size="sm" variant="outline">{m.common.view}</Button>
                  </Link>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Briefcase className="h-4 w-4" /> {m.work.myTasks}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <TaskList items={hub.my_tasks} empty={m.work.noAssigned} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{m.work.createdByMe}</CardTitle>
          </CardHeader>
          <CardContent>
            <TaskList items={hub.tasks_created_by_me} empty="Sin tareas creadas por ti." />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
