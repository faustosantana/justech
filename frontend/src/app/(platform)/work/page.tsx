"use client";

import Link from "next/link";
import { AlertTriangle, Briefcase, ClipboardList, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { t } from "@/i18n";
import { apiClient } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import { PRIORITY_LABELS, priorityClass, type WorkHub } from "@/lib/tasks";
import { cn } from "@/lib/utils";

const m = t();

function TaskList({ items, empty }: { items: WorkHub["my_tasks"]; empty: string }) {
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">{empty}</p>;
  }
  return (
    <div className="space-y-2">
      {items.slice(0, 8).map((t) => (
        <Link
          key={t.id}
          href={`/tasks/${t.id}`}
          className="flex items-center justify-between rounded-lg border border-border p-3 hover:bg-muted/30"
        >
          <div>
            <p className="text-sm font-medium">{t.title}</p>
            <p className="text-xs text-muted-foreground">
              {m.tasks.dueDate}: {t.due_date ?? m.common.none}
              {t.assigned_to_name && ` · ${t.assigned_to_name}`}
            </p>
          </div>
          <span className={cn("rounded-full px-2 py-0.5 text-xs", priorityClass(t.priority))}>
            {PRIORITY_LABELS[t.priority]}
          </span>
        </Link>
      ))}
    </div>
  );
}

export default function WorkHubPage() {
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
    load();
  }, [load]);

  return (
    <AppShell title={m.work.title} description={m.work.description}>
      <div className="space-y-6">
        <div className="flex justify-end">
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={cn("mr-2 h-4 w-4", loading && "animate-spin")} />
            {m.common.refresh}
          </Button>
        </div>

        {loading || !hub ? (
          <p className="text-sm text-muted-foreground">{m.common.loading}</p>
        ) : (
          <>
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
                    <p className="text-xs text-muted-foreground uppercase tracking-wide">{kpi.label}</p>
                    <p className={cn("text-3xl font-bold", kpi.color)}>{kpi.value}</p>
                  </CardContent>
                </Card>
              ))}
            </div>

            {hub.alerts.length > 0 && (
              <Card className="border-amber-500/30">
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-amber-400" />
                    {m.work.operationalAlerts}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {hub.alerts.map((a) => (
                    <div key={a.type} className="flex items-center justify-between rounded-lg border border-border p-3">
                      <div>
                        <p className="font-medium text-sm">{a.title}</p>
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
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Briefcase className="h-4 w-4" /> {m.work.myTasks}
                  </CardTitle>
                  <Link href="/tasks"><Button size="sm" variant="ghost">{m.common.viewAll}</Button></Link>
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

            <div className="grid gap-6 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">{m.work.supervisedByMe}</CardTitle>
                </CardHeader>
                <CardContent>
                  <TaskList items={hub.tasks_supervised_by_me} empty="Sin tareas supervisadas." />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-base">{m.work.byDepartment}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {hub.by_department.map((d) => (
                      <div key={d.department} className="flex justify-between text-sm rounded-lg border border-border p-2 capitalize">
                        <span>{d.department}</span>
                        <span className="text-muted-foreground">
                          {d.pending} pend. · {d.overdue} venc. · {d.critical} crit.
                        </span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <ClipboardList className="h-4 w-4" /> {m.work.recentActivity}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {hub.recent_activity.slice(0, 10).map((a, i) => (
                    <div key={i} className="text-sm border-b border-border/50 pb-2">
                      <span className="text-muted-foreground">{a.user_name || "Sistema"}</span>
                      {" · "}{a.action}
                      {a.task_title && (
                        <> — <Link href={`/tasks/${a.task_id}`} className="text-primary hover:underline">{a.task_title}</Link></>
                      )}
                    </div>
                  ))}
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="text-base">{m.work.recentNotifications}</CardTitle>
                  <Link href="/notifications">
                    <Button size="sm" variant="ghost">
                      {m.common.viewAll} ({hub.unread_notifications} sin leer)
                    </Button>
                  </Link>
                </CardHeader>
                <CardContent className="space-y-2">
                  {hub.recent_notifications.map((n) => (
                    <div key={n.id} className={cn("rounded-lg border p-3 text-sm", !n.is_read && "border-primary/30 bg-primary/5")}>
                      <p className="font-medium">{n.title}</p>
                      <p className="text-xs text-muted-foreground">{n.message}</p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader><CardTitle className="text-base">{m.work.quickActions}</CardTitle></CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                <Link href="/tasks"><Button size="sm">{m.tasks.newTask}</Button></Link>
                <Link href="/tasks"><Button size="sm" variant="outline">{m.common.viewAll} {m.nav.tasks.toLowerCase()}</Button></Link>
                <Link href="/odoo"><Button size="sm" variant="outline">Desde Odoo</Button></Link>
                <Link href="/dgcp"><Button size="sm" variant="outline">Desde DGCP</Button></Link>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </AppShell>
  );
}
