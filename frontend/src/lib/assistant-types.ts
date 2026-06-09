export interface SalesReportMetric {
  label: string;
  value: string;
}

export interface AssistantAction {
  label: string;
  type: "internal_link" | "external_link" | "quick_view" | string;
  url?: string;
  entity_type?: string;
  entity_id?: string;
}

export interface AssistantTableRow {
  cells: string[];
  entity_type?: string;
  entity_id?: string;
  actions?: AssistantAction[];
}

export interface AssistantDataTableDef {
  title: string;
  columns: string[];
  rows: (string[] | AssistantTableRow)[];
}

export interface BusinessAnswerLink {
  label: string;
  url: string;
  type: string;
}

export interface StructuredAnswerBase {
  summary: string;
  metrics: SalesReportMetric[];
  tables: AssistantDataTableDef[];
  warnings: string[];
  actions?: AssistantAction[];
}

export interface SalesReport extends StructuredAnswerBase {
  type: "sales_report";
}

export interface BusinessAnswer extends StructuredAnswerBase {
  type: "business_answer";
  intent: string;
  source: string;
  links: BusinessAnswerLink[];
}

export function normalizeTableRow(row: string[] | AssistantTableRow): AssistantTableRow {
  if (Array.isArray(row)) {
    return { cells: row };
  }
  return row;
}

export function isSalesReport(data: unknown): data is SalesReport {
  return (
    typeof data === "object" &&
    data !== null &&
    (data as SalesReport).type === "sales_report" &&
    Array.isArray((data as SalesReport).metrics) &&
    Array.isArray((data as SalesReport).tables)
  );
}

export function isBusinessAnswer(data: unknown): data is BusinessAnswer {
  return (
    typeof data === "object" &&
    data !== null &&
    (data as BusinessAnswer).type === "business_answer" &&
    Array.isArray((data as BusinessAnswer).metrics) &&
    Array.isArray((data as BusinessAnswer).tables)
  );
}

export function isStructuredAnswer(data: unknown): data is BusinessAnswer | SalesReport {
  return isBusinessAnswer(data) || isSalesReport(data);
}

export interface QuickViewTarget {
  entity_type: string;
  entity_id: string;
  label?: string;
}
