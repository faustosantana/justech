export interface ExecutiveKpi {
  id: string;
  label: string;
  value: string;
  source: string;
  href?: string | null;
  tone?: string;
  delta?: string | null;
}

export interface ModuleSnapshot {
  id: string;
  label: string;
  status: string;
  metrics: string[];
  href: string;
}

export interface ExecutiveAlert {
  id: string;
  title: string;
  priority: string;
  source: string;
  href: string;
  assignee?: string | null;
}

export interface ExecutiveActivityItem {
  id: string;
  title: string;
  subtitle: string;
  timestamp?: string | null;
  href?: string | null;
}

export interface ExecutiveDashboard {
  user_name: string;
  tenant_name: string;
  company_name?: string | null;
  updated_at: string;
  proactive_message: string;
  assistant_suggestions: string[];
  kpis: ExecutiveKpi[];
  modules: ModuleSnapshot[];
  alerts: ExecutiveAlert[];
  activity: ExecutiveActivityItem[];
}
