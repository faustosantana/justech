/** Microsoft 365 Operativo — tipos API Fase 6 */

export interface M365SuggestedAction {
  key: string;
  label: string;
  description?: string;
  confidence?: number;
  href?: string;
  auto_eligible?: boolean;
}

export interface M365EmailRelation {
  entity_type: string;
  entity_id?: string | null;
  label: string;
  confidence?: number;
  href?: string | null;
  metadata?: Record<string, unknown>;
}

export interface M365ProcessedEmail {
  id: string;
  mailbox: string;
  external_message_id: string;
  subject: string;
  sender_email: string;
  sender_name?: string | null;
  received_at: string;
  body_preview?: string | null;
  classification: string;
  classification_label: string;
  classification_confidence: number;
  extracted_data: Record<string, unknown>;
  relations: M365EmailRelation[];
  suggested_actions: M365SuggestedAction[];
  attachments: Record<string, unknown>[];
  sharepoint_path?: string | null;
  processing_status: string;
  graph_connected: boolean;
  demo_source: boolean;
  hermes_indexed: boolean;
  related_dgcp_process_id?: string | null;
  related_task_id?: string | null;
  amount?: number | null;
  currency?: string | null;
}

export interface M365OperativeDashboard {
  graph_connected: boolean;
  demo_mode: boolean;
  mailboxes_monitored: number;
  emails_today: number;
  attachments_processed: number;
  quotes_detected: number;
  invoices_detected: number;
  purchase_orders_detected: number;
  dgcp_documents_detected: number;
  tasks_generated: number;
  documents_indexed: number;
  pending_actions: number;
  recent_emails: M365ProcessedEmail[];
  briefing_lines: string[];
  quick_actions: M365SuggestedAction[];
}

export interface M365ProcessedEmailListResponse {
  items: M365ProcessedEmail[];
  total: number;
  graph_connected: boolean;
  demo_mode: boolean;
  message?: string | null;
}

export interface M365SyncResponse {
  ingested: number;
  processed: number;
  skipped: number;
  graph_connected: boolean;
  demo_mode: boolean;
  message: string;
}

export interface M365ExecuteActionResponse {
  status: string;
  action_key: string;
  message: string;
  result: Record<string, unknown>;
  task_id?: string | null;
  notification_id?: string | null;
}
