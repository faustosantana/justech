export interface HermesCardAction {
  action: string;
  label: string;
  requires_approval: boolean;
}

export interface HermesCard {
  id: string;
  type: string;
  title: string;
  summary: string;
  priority: string;
  source: string;
  recommendation: string;
  date?: string | null;
  href?: string | null;
  suggested_actions?: HermesCardAction[];
  metadata?: Record<string, unknown>;
}
