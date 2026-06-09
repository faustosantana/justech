"use client";

import Link from "next/link";
import { ClipboardList, Plus, RefreshCw, Search } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { BulkActionsBar } from "@/components/ui/bulk-actions-bar";
import { UserSelector } from "@/components/work/user-selector";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { t } from "@/i18n";
import { apiClient } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import {
  PRIORITY_LABELS,
  STATUS_LABELS,
  priorityClass,
  statusClass,
  type Task,
  type TaskPriority,
  type TaskStatus,
} from "@/lib/tasks";
import { cn } from "@/lib/utils";

const m = t();
const STATUSES: TaskStatus[] = ["pendiente", "en_proceso", "completada", "vencida"];
const PRIORITIES: TaskPriority[] = ["critica", "alta", "media", "baja"];

export default function TasksPage() {
  const router = useRouter();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [assigneeId, setAssigneeId] = useState<string | null>(null);
  const [supervisorId, setSupervisorId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const load = useCallback(async () => {
    if (!getAccessToken()) {
      router.replace("/login");
      return;
    }
    setLoading(true);
    try {
      const res = await apiClient.getTasks({
        search: search || undefined,
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
        limit: 100,
      });
      setTasks(res.items);
      setTotal(res.total);
      setSelectedIds([]);
    } finally {
      setLoading(false);
    }
  }, [router, search, statusFilter, priorityFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    setCreating(true);
    try {
      const task = await apiClient.createTask({
        title: newTitle.trim(),
        description: newDesc || undefined,
        assigned_to_id: assigneeId || undefined,
        supervisor_id: supervisorId || undefined,
      });
      setShowCreate(false);
      setNewTitle("");
      setNewDesc("");
      setAssigneeId(null);
      setSupervisorId(null);
      router.push(`/tasks/${task.id}`);
    } finally {
      setCreating(false);
    }
  };

  return (
    <AppShell title={m.tasks.title} description={m.tasks.description}>
      <div className="space-y-6">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              className="w-full rounded-lg border border-border bg-background py-2 pl-9 pr-3 text-sm"
              placeholder={m.tasks.searchTasks}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <select
            className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label={m.common.filter}
          >
            <option value="">{m.tasks.allStatuses}</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>{STATUS_LABELS[s]}</option>
            ))}
          </select>
          <select
            className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            aria-label={m.common.filter}
          >
            <option value="">{m.tasks.allPriorities}</option>
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>{PRIORITY_LABELS[p]}</option>
            ))}
          </select>
          <Button variant="outline" size="sm" onClick={load} disabled={loading} title={m.common.refresh}>
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
          </Button>
          <Button size="sm" onClick={() => setShowCreate(true)}>
            <Plus className="mr-2 h-4 w-4" />
            {m.tasks.newTask}
          </Button>
        </div>

        <BulkActionsBar
          selectedIds={selectedIds}
          allIds={tasks.map((t) => t.id)}
          onSelectAll={() => setSelectedIds(tasks.map((t) => t.id))}
          onClearSelection={() => setSelectedIds([])}
          actions={[
            {
              id: "archive",
              label: "Archivar",
              variant: "destructive",
              onRun: async (ids) => {
                const res = await apiClient.bulkTasks({ ids, action: "archive" });
                await load();
                return res.message;
              },
            },
            {
              id: "status-pending",
              label: "Marcar pendiente",
              onRun: async (ids) => {
                const res = await apiClient.bulkTasks({ ids, action: "status", status: "pendiente" });
                await load();
                return res.message;
              },
            },
          ]}
        />

        {showCreate && (
          <Card>
            <CardHeader><CardTitle className="text-base">{m.tasks.createManual}</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <input
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                placeholder={m.tasks.titlePlaceholder}
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
              />
              <textarea
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
                placeholder={m.tasks.descriptionPlaceholder}
                rows={3}
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
              />
              <div className="grid gap-4 sm:grid-cols-2">
                <UserSelector
                  label={m.tasks.assignee}
                  value={assigneeId}
                  onChange={(id) => setAssigneeId(id)}
                  placeholder={m.tasks.searchUser}
                />
                <UserSelector
                  label={m.tasks.supervisor}
                  value={supervisorId}
                  onChange={(id) => setSupervisorId(id)}
                  placeholder={m.tasks.searchUser}
                  emptyLabel="Sin supervisor"
                />
              </div>
              <div className="flex gap-2">
                <Button onClick={handleCreate} disabled={creating}>
                  {creating ? m.tasks.creating : m.common.create}
                </Button>
                <Button variant="outline" onClick={() => setShowCreate(false)}>{m.common.cancel}</Button>
              </div>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <ClipboardList className="h-4 w-4" />
              {m.nav.tasks} ({total})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="text-sm text-muted-foreground">{m.common.loading}</p>
            ) : tasks.length === 0 ? (
              <p className="text-sm text-muted-foreground">{m.tasks.noTasks}</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-muted-foreground">
                      <th className="pb-2 pr-2 w-8" />
                      <th className="pb-2 pr-4">Tarea</th>
                      <th className="pb-2 pr-4">{m.common.status}</th>
                      <th className="pb-2 pr-4">Prioridad</th>
                      <th className="pb-2 pr-4">{m.tasks.assignee}</th>
                      <th className="pb-2 pr-4">Departamento</th>
                      <th className="pb-2">{m.tasks.dueDate}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tasks.map((t) => (
                      <tr key={t.id} className="border-b border-border/50 hover:bg-muted/30">
                        <td className="py-3 pr-2">
                          <input
                            type="checkbox"
                            checked={selectedIds.includes(t.id)}
                            onChange={(e) =>
                              setSelectedIds((prev) =>
                                e.target.checked
                                  ? [...prev, t.id]
                                  : prev.filter((id) => id !== t.id),
                              )
                            }
                          />
                        </td>
                        <td className="py-3 pr-4">
                          <Link href={`/tasks/${t.id}`} className="font-medium text-primary hover:underline">
                            {t.title}
                          </Link>
                          {t.customer_name && (
                            <p className="text-xs text-muted-foreground">{t.customer_name}</p>
                          )}
                        </td>
                        <td className="py-3 pr-4">
                          <span className={cn("rounded-full px-2 py-0.5 text-xs", statusClass(t.status))}>
                            {STATUS_LABELS[t.status as TaskStatus] ?? t.status}
                          </span>
                        </td>
                        <td className="py-3 pr-4">
                          <span className={cn("rounded-full px-2 py-0.5 text-xs", priorityClass(t.priority))}>
                            {PRIORITY_LABELS[t.priority as TaskPriority] ?? t.priority}
                          </span>
                        </td>
                        <td className="py-3 pr-4 text-muted-foreground">
                          {t.assigned_to_name || t.suggested_assignee_name || m.common.none}
                          {t.assigned_to_email && (
                            <p className="text-xs">{t.assigned_to_email}</p>
                          )}
                        </td>
                        <td className="py-3 pr-4 capitalize text-muted-foreground">{t.department}</td>
                        <td className="py-3 text-muted-foreground">{t.due_date ?? m.common.none}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
