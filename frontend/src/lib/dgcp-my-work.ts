/** Tipos — Mis Licitaciones / checklist preparación */

export type TrafficLight = "green" | "yellow" | "orange" | "red" | "black" | "none";

export interface ChecklistProgress {
  completed: number;
  applicable: number;
  pct: number;
}

export interface PrepTask {
  id: string;
  opportunity_id: string;
  title: string;
  description?: string | null;
  status: string;
  priority: string;
  assigned_user_id?: string | null;
  assigned_user_name?: string | null;
  due_at?: string | null;
  template_item_key?: string | null;
  completed_at?: string | null;
  traffic_light?: TrafficLight;
  hours_remaining?: number | null;
}

export interface MyLicitacionRow {
  opportunity_id: string;
  code: string;
  institution: string;
  title: string;
  company: string;
  status: string;
  status_label: string;
  process_deadline?: string | null;
  process_traffic_light: TrafficLight;
  process_hours_remaining?: number | null;
  responsible_user_id?: string | null;
  responsible_name?: string | null;
  checklist_progress: ChecklistProgress;
  next_pending_title?: string | null;
  next_pending_due_at?: string | null;
  priority: string;
}

export interface MyWorkSummary {
  require_attention_today: number;
  due_in_3_days: number;
  in_preparation: number;
  overdue_tasks: number;
  new_awards: number;
}

export interface MyLicitacionesResponse {
  summary: MyWorkSummary;
  items: MyLicitacionRow[];
  total: number;
  scope: string;
}

export interface HoyItem {
  kind: string;
  sort_rank: number;
  title: string;
  opportunity_id: string;
  opportunity_code: string;
  institution: string;
  due_at?: string | null;
  task_id?: string | null;
  priority?: string | null;
  status?: string | null;
}

export interface HoyResponse {
  items: HoyItem[];
  total: number;
}

export interface MisPendientesResponse {
  items: PrepTask[];
  total: number;
  opportunity_code: Record<string, string>;
  institution: Record<string, string>;
}

export interface PrepChecklistResponse {
  opportunity_id: string;
  process_deadline?: string | null;
  responsible_user_id?: string | null;
  responsible_name?: string | null;
  progress: ChecklistProgress;
  next_pending?: PrepTask | null;
  items: PrepTask[];
}

export interface ApplyTemplateResponse {
  opportunity_id: string;
  template_id: string;
  created: number;
  skipped_duplicates: number;
  items: PrepTask[];
}

export interface ChecklistTemplate {
  id: string;
  name: string;
  description?: string | null;
  is_default: boolean;
  is_active: boolean;
  items: Array<{
    item_key: string;
    title: string;
    description?: string | null;
    priority: string;
    sort_order: number;
    default_offset_hours?: number | null;
  }>;
}

export interface ChecklistTemplateCreate {
  name: string;
  description?: string;
  is_default?: boolean;
  items: ChecklistTemplate["items"];
}

export function trafficDot(light?: TrafficLight | null): string {
  switch (light) {
    case "green":
      return "🟢";
    case "yellow":
      return "🟡";
    case "orange":
      return "🟠";
    case "red":
      return "🔴";
    case "black":
      return "⚫";
    default:
      return "⚪";
  }
}

export function formatRemaining(hours?: number | null): string {
  if (hours == null) return "—";
  if (hours < 0) return `Vencido hace ${Math.abs(Math.round(hours))}h`;
  if (hours < 24) return `Faltan ${Math.round(hours)}h`;
  return `Faltan ${Math.round(hours / 24)} días`;
}
