export type {
  AssistantAction,
  AssistantDataTableDef,
  AssistantTableRow,
  BusinessAnswer,
  BusinessAnswerLink,
  QuickViewTarget,
  SalesReport,
  SalesReportMetric,
  StructuredAnswerBase,
} from "@/lib/assistant-types";

export {
  isBusinessAnswer,
  isSalesReport,
  isStructuredAnswer,
  normalizeTableRow,
} from "@/lib/assistant-types";

export interface AssistantLink {
  label: string;
  url: string;
  type: string;
}

export interface AssistantCard {
  title: string;
  subtitle?: string | null;
  fields: Record<string, string>;
  link?: string | null;
}

export interface AssistantQueryRequest {
  question: string;
  current_module?: string | null;
  current_company_context?: number | null;
  current_record_id?: string | null;
  record_type?: string | null;
  conversation_id?: string | null;
  debug_context?: boolean;
}

export interface AssistantQueryResponse {
  question: string;
  answer: string;
  sources: string[];
  query_type: string;
  cards: AssistantCard[];
  links: AssistantLink[];
  actions?: import("@/lib/assistant-types").AssistantAction[];
  data: Record<string, unknown>;
  structured_data?: import("@/lib/assistant-types").BusinessAnswer | import("@/lib/assistant-types").SalesReport | Record<string, unknown> | null;
  read_only_notice?: string | null;
  resolved_question?: string | null;
  conversation_context?: Record<string, unknown> | null;
  was_follow_up?: boolean;
}

export interface AssistantMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  response?: AssistantQueryResponse;
  timestamp: number;
}

const STORAGE_KEY = "jaios_assistant_history";

export function loadAssistantHistory(): AssistantMessage[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as AssistantMessage[]) : [];
  } catch {
    return [];
  }
}

export function saveAssistantHistory(messages: AssistantMessage[]): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-50)));
}

export function sourceBadgeColor(source: string): string {
  switch (source.toLowerCase()) {
    case "odoo":
      return "bg-accent text-accent-foreground border border-primary/15";
    case "dgcp":
      return "bg-primary/10 text-primary border border-primary/20";
    case "documents":
    case "m365":
      return "bg-secondary/10 text-secondary border border-secondary/20";
    default:
      return "bg-muted text-muted-foreground border border-border";
  }
}
