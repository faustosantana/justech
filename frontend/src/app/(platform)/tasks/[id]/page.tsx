"use client";

import Link from "next/link";
import { ArrowLeft, CheckSquare, MessageSquare, UserCog } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { UserSelector } from "@/components/work/user-selector";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { t } from "@/i18n";
import { apiClient } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import {
  ASSIGNMENT_ACTION_LABELS,
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
const STATUSES: TaskStatus[] = [
  "pendiente", "en_proceso", "esperando_tercero", "en_revision", "completada", "cancelada",
];

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [comment, setComment] = useState("");
  const [newCheckItem, setNewCheckItem] = useState("");
  const [saving, setSaving] = useState(false);
  const [editAssignee, setEditAssignee] = useState(false);
  const [assigneeId, setAssigneeId] = useState<string | null>(null);
  const [supervisorId, setSupervisorId] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id || !getAccessToken()) return;
    try {
      const t = await apiClient.getTask(id);
      setTask(t);
      setAssigneeId(t.assigned_to_id);
      setSupervisorId(t.supervisor_id);
    } catch {
      router.replace("/tasks");
    } finally {
      setLoading(false);
    }
  }, [id, router]);

  useEffect(() => {
    load();
  }, [load]);

  const updateStatus = async (status: string) => {
    if (!task) return;
    setSaving(true);
    try {
      const updated = await apiClient.updateTask(task.id, { status });
      setTask(updated);
    } finally {
      setSaving(false);
    }
  };

  const saveAssignment = async () => {
    if (!task) return;
    setSaving(true);
    try {
      const updated = await apiClient.updateTask(task.id, {
        assigned_to_id: assigneeId,
        supervisor_id: supervisorId,
      });
      setTask(updated);
      setEditAssignee(false);
    } finally {
      setSaving(false);
    }
  };

  const submitComment = async () => {
    if (!task || !comment.trim()) return;
    setSaving(true);
    try {
      const updated = await apiClient.addTaskComment(task.id, comment.trim());
      setTask(updated);
      setComment("");
    } finally {
      setSaving(false);
    }
  };

  const addChecklist = async () => {
    if (!task || !newCheckItem.trim()) return;
    setSaving(true);
    try {
      const updated = await apiClient.addTaskChecklistItem(task.id, newCheckItem.trim());
      setTask(updated);
      setNewCheckItem("");
    } finally {
      setSaving(false);
    }
  };

  const toggleChecklist = async (itemId: string, completed: boolean) => {
    if (!task) return;
    const updated = await apiClient.updateTaskChecklistItem(task.id, itemId, completed);
    setTask(updated);
  };

  if (loading) {
    return (
      <AppShell title={m.tasks.title}>
        <p className="text-sm text-muted-foreground">{m.common.loading}</p>
      </AppShell>
    );
  }

  if (!task) return null;

  return (
    <AppShell title={task.title} description={`${task.category} · ${task.department}`}>
      <div className="space-y-6">
        <Link href="/tasks" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> {m.common.back} a {m.nav.tasks.toLowerCase()}
        </Link>

        {task.assignee_resolution_warning && (
          <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
            {task.assignee_resolution_warning}
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            <Card>
              <CardContent className="pt-6 space-y-4">
                <div className="flex flex-wrap gap-2">
                  <span className={cn("rounded-full px-2.5 py-1 text-xs font-medium", statusClass(task.status))}>
                    {STATUS_LABELS[task.status]}
                  </span>
                  <span className={cn("rounded-full px-2.5 py-1 text-xs font-medium", priorityClass(task.priority))}>
                    {PRIORITY_LABELS[task.priority as TaskPriority]}
                  </span>
                  <span className="rounded-full bg-muted px-2.5 py-1 text-xs capitalize">{task.category}</span>
                </div>
                {task.description && (
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">{task.description}</p>
                )}
                <div className="grid gap-2 sm:grid-cols-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">{m.tasks.assignee}:</span>{" "}
                    {task.assigned_to_name || task.suggested_assignee_name || m.common.none}
                    {task.assigned_to_email && <span className="block text-xs text-muted-foreground">{task.assigned_to_email}</span>}
                  </div>
                  <div>
                    <span className="text-muted-foreground">{m.tasks.supervisor}:</span>{" "}
                    {task.supervisor_name || m.common.none}
                    {task.supervisor_email && <span className="block text-xs text-muted-foreground">{task.supervisor_email}</span>}
                  </div>
                  <div>
                    <span className="text-muted-foreground">{m.tasks.creator}:</span>{" "}
                    {task.created_by_name || m.common.none}
                    {task.created_by_email && <span className="block text-xs text-muted-foreground">{task.created_by_email}</span>}
                  </div>
                  <div><span className="text-muted-foreground">{m.tasks.dueDate}:</span> {task.due_date ?? m.common.none}</div>
                  <div><span className="text-muted-foreground">{m.tasks.createdAt}:</span> {new Date(task.created_at).toLocaleString("es-DO")}</div>
                  <div><span className="text-muted-foreground">{m.tasks.completedAt}:</span> {task.completed_at ? new Date(task.completed_at).toLocaleString("es-DO") : m.common.none}</div>
                  <div><span className="text-muted-foreground">{m.tasks.source}:</span> {task.source}</div>
                  {task.customer_name && <div><span className="text-muted-foreground">{m.tasks.customer}:</span> {task.customer_name}</div>}
                </div>
                <div className="flex flex-wrap gap-2 pt-2">
                  {STATUSES.map((s) => (
                    <Button
                      key={s}
                      size="sm"
                      variant={task.status === s ? "default" : "outline"}
                      onClick={() => updateStatus(s)}
                      disabled={saving}
                    >
                      {STATUS_LABELS[s]}
                    </Button>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <UserCog className="h-4 w-4" /> {m.tasks.changeAssignee}
                </CardTitle>
                <Button size="sm" variant="ghost" onClick={() => setEditAssignee(!editAssignee)}>
                  {editAssignee ? m.common.cancel : m.common.update}
                </Button>
              </CardHeader>
              {editAssignee && (
                <CardContent className="space-y-4">
                  <UserSelector label={m.tasks.assignee} value={assigneeId} onChange={(id) => setAssigneeId(id)} />
                  <UserSelector label={m.tasks.supervisor} value={supervisorId} onChange={(id) => setSupervisorId(id)} emptyLabel="Sin supervisor" />
                  <Button size="sm" onClick={saveAssignment} disabled={saving}>{m.common.save}</Button>
                </CardContent>
              )}
            </Card>

            {task.assignment_history.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">{m.tasks.assignmentHistory}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {task.assignment_history.map((h, i) => (
                    <div key={i} className="text-sm border-b border-border/50 pb-2">
                      <span className="font-medium">{ASSIGNMENT_ACTION_LABELS[h.action] ?? h.action}</span>
                      {h.user_name && <span className="text-muted-foreground"> · {h.user_name}</span>}
                      <span className="text-xs text-muted-foreground block">
                        {new Date(h.created_at).toLocaleString("es-DO")}
                      </span>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <CheckSquare className="h-4 w-4" /> {m.tasks.checklist}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {task.checklist_items.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Sin ítems.</p>
                ) : (
                  task.checklist_items.map((item) => (
                    <label key={item.id} className="flex items-start gap-3 text-sm cursor-pointer">
                      <input
                        type="checkbox"
                        checked={item.completed}
                        onChange={(e) => toggleChecklist(item.id, e.target.checked)}
                        className="mt-1"
                      />
                      <span className={item.completed ? "line-through text-muted-foreground" : ""}>{item.text}</span>
                    </label>
                  ))
                )}
                <div className="flex gap-2 pt-2">
                  <input
                    className="flex-1 rounded-lg border border-border bg-background px-3 py-1.5 text-sm"
                    placeholder="Nuevo ítem de lista"
                    value={newCheckItem}
                    onChange={(e) => setNewCheckItem(e.target.value)}
                  />
                  <Button size="sm" variant="secondary" onClick={addChecklist} disabled={saving}>{m.common.add}</Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <MessageSquare className="h-4 w-4" /> {m.tasks.comments}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {task.comments.map((c) => (
                  <div key={c.id} className="rounded-lg border border-border p-3">
                    <p className="text-xs text-muted-foreground mb-1">
                      {c.user_name || "Usuario"} · {new Date(c.created_at).toLocaleString("es-DO")}
                    </p>
                    <p className="text-sm">{c.comment}</p>
                  </div>
                ))}
                <div className="flex gap-2">
                  <input
                    className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm"
                    placeholder="Escribir comentario…"
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                  />
                  <Button size="sm" onClick={submitComment} disabled={saving}>{m.common.send}</Button>
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-4">
            <Card>
              <CardHeader><CardTitle className="text-base">{m.tasks.links}</CardTitle></CardHeader>
              <CardContent className="space-y-2 text-sm">
                {task.odoo_customer_id && (
                  <Link href={`/odoo/customers/${task.odoo_customer_id}`} className="text-primary hover:underline block">
                    Cliente Odoo #{task.odoo_customer_id}
                  </Link>
                )}
                {task.odoo_invoice_id && (
                  <Link href={`/odoo/invoices/${task.odoo_invoice_id}`} className="text-primary hover:underline block">
                    Factura Odoo #{task.odoo_invoice_id}
                  </Link>
                )}
                {task.dgcp_process_id && (
                  <Link href={`/dgcp/${task.dgcp_process_id}`} className="text-primary hover:underline block">
                    Proceso DGCP
                  </Link>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
