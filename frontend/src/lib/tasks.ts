/** Work Operations Center — tipos y etiquetas */

export type TaskStatus =
  | "pendiente"
  | "en_proceso"
  | "esperando_tercero"
  | "en_revision"
  | "completada"
  | "vencida"
  | "cancelada";

export type TaskPriority = "baja" | "media" | "alta" | "critica";

export interface TaskComment {
  id: string;
  user_id: string | null;
  user_name: string | null;
  comment: string;
  created_at: string;
}

export interface TaskChecklistItem {
  id: string;
  text: string;
  completed: boolean;
  completed_by_id: string | null;
  completed_by_name: string | null;
  completed_at: string | null;
  sort_order: number;
}

export interface TaskAssignmentHistory {
  action: string;
  user_name: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface Task {
  id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  priority: TaskPriority;
  category: string;
  department: string;
  source: string;
  created_by_id: string | null;
  created_by_name: string | null;
  created_by_email: string | null;
  assigned_to_id: string | null;
  assigned_to_name: string | null;
  assigned_to_email: string | null;
  supervisor_id: string | null;
  supervisor_name: string | null;
  supervisor_email: string | null;
  suggested_assignee_name: string | null;
  assignee_resolution_warning: string | null;
  assignment_history: TaskAssignmentHistory[];
  due_date: string | null;
  completed_at: string | null;
  customer_name: string | null;
  odoo_customer_id: number | null;
  odoo_invoice_id: number | null;
  odoo_quotation_id: number | null;
  dgcp_process_id: string | null;
  amount: string | null;
  currency: string;
  tags: string[];
  metadata: Record<string, unknown>;
  comments: TaskComment[];
  checklist_items: TaskChecklistItem[];
  attachments: { id: string; name: string; file_type: string | null }[];
  created_at: string;
  updated_at: string;
}

export interface TaskListResponse {
  items: Task[];
  total: number;
}

export interface Notification {
  id: string;
  user_id: string;
  title: string;
  message: string;
  type: string;
  severity: string;
  is_read: boolean;
  related_task_id: string | null;
  created_at: string;
  read_at: string | null;
}

export interface NotificationListResponse {
  items: Notification[];
  total: number;
  unread_count: number;
}

export interface WorkHub {
  my_tasks: Task[];
  my_pending: number;
  my_in_progress: number;
  my_overdue: number;
  my_critical: number;
  my_due_soon: number;
  tasks_created_by_me: Task[];
  tasks_supervised_by_me: Task[];
  by_department: { department: string; pending: number; overdue: number; critical: number }[];
  alerts: { type: string; title: string; message: string; count: number; severity: string; link: string | null }[];
  recent_activity: { action: string; task_id: string | null; task_title: string | null; user_name: string | null; created_at: string }[];
  recent_notifications: Notification[];
  unread_notifications: number;
}

export interface RoutingPreview {
  event_type: string;
  category: string;
  department: string;
  priority: string;
  suggested_assignee_name: string | null;
  suggested_supervisor_name: string | null;
  assignee_resolved: boolean;
  supervisor_resolved: boolean;
  resolution_warning: string | null;
  due_date: string | null;
  notification_message: string;
  checklist: string[];
  matched_rule: string;
}

export const ASSIGNMENT_ACTION_LABELS: Record<string, string> = {
  assigned: "Asignación",
  reassigned: "Reasignación",
  supervisor_changed: "Cambio de supervisor",
  completed: "Completada",
};

export const NOTIFICATION_TYPE_LABELS: Record<string, string> = {
  task_assigned: "Tarea asignada",
  task_reassigned: "Tarea reasignada",
  task_due_soon: "Por vencer",
  task_overdue: "Vencida",
  task_commented: "Comentario",
  task_completed: "Completada",
  task_updated: "Actualizada",
};

export const STATUS_LABELS: Record<TaskStatus, string> = {
  pendiente: "Pendiente",
  en_proceso: "En proceso",
  esperando_tercero: "Esperando tercero",
  en_revision: "En revisión",
  completada: "Completada",
  vencida: "Vencida",
  cancelada: "Cancelada",
};

export const PRIORITY_LABELS: Record<TaskPriority, string> = {
  baja: "Baja",
  media: "Media",
  alta: "Alta",
  critica: "Crítica",
};

export function priorityClass(p: string): string {
  if (p === "critica") return "text-red-400 bg-red-500/10";
  if (p === "alta") return "text-orange-400 bg-orange-500/10";
  if (p === "media") return "text-amber-400 bg-amber-500/10";
  return "text-muted-foreground bg-muted";
}

export function statusClass(s: string): string {
  if (s === "completada") return "text-success bg-success/10";
  if (s === "vencida") return "text-destructive bg-destructive/10";
  if (s === "en_proceso") return "text-primary bg-primary/10";
  return "text-muted-foreground bg-muted";
}
