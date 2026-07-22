/** Tipos y helpers del módulo Resultados de Loterías. */

export interface LotteryHealth {
  module_enabled: boolean;
  database_connection: boolean;
  schema_available: boolean;
  import_status: string;
  sync_status: string;
  timestamp: string;
  version: string;
  lotteries_count: number;
  draws_count: number;
  note?: string | null;
}

export interface LotteryLottery {
  id: string;
  source_id: number;
  name: string;
  normalized_name: string;
  slug: string;
  country?: string | null;
  timezone: string;
  active: boolean;
  is_loto: boolean;
  is_aggregate: boolean;
  first_draw_date?: string | null;
  last_draw_date?: string | null;
  draw_count: number;
}

export interface LotteryListResponse {
  items: LotteryLottery[];
  total: number;
  module_enabled: boolean;
  note?: string | null;
}

export interface DrawNumberResult {
  position: number;
  position_label: string;
  number_value: string;
  number_raw: string;
  number_type: string;
}

export interface DrawResult {
  id: string;
  draw_date: string;
  draw_time?: string | null;
  game_name: string;
  source_reference?: string | null;
  numbers: DrawNumberResult[];
}

export interface DateQueryResponse {
  date: string;
  total: number;
  draws: DrawResult[];
  meta: {
    resolved_lottery?: LotteryLottery | null;
    warnings: { code: string; message: string }[];
  };
}

export interface CalendarWindowResponse {
  days_requested: number;
  calendar_from: string;
  calendar_to: string;
  days_with_draws: string[];
  days_without_draws: string[];
  total_draws: number;
  draws: DrawResult[];
  meta: { query: Record<string, unknown>; warnings: { code: string; message: string }[] };
}

export interface DrawsWindowResponse {
  count_requested: number;
  total: number;
  draws: DrawResult[];
  meta: { query: Record<string, unknown> };
}

export interface FrequencyResponse {
  from_date: string;
  to_date: string;
  total_observations: number;
  items: { number: string; count: number; percentage: number }[];
}

export interface ComparisonResponse {
  mode: string;
  from_date: string;
  to_date: string;
  lotteries: LotteryLottery[];
  data: Record<string, unknown>;
}

const LOTTERY_ROLES = new Set(["owner", "admin", "gerencia", "lottery_client"]);

export function canAccessLotteryModule(role: string | null): boolean {
  if (!role) return false;
  return LOTTERY_ROLES.has(role);
}

export function isLotteryClientRole(role: string | null): boolean {
  return role === "lottery_client";
}

export const DISCLAIMER =
  "Los resultados históricos y las estadísticas son únicamente informativos. No garantizan resultados futuros.";

export interface LotteryChatSession {
  id: string;
  title?: string | null;
  context: Record<string, unknown>;
  last_message_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface LotteryChatMessage {
  id: string;
  role: string;
  content: string;
  tool_name?: string | null;
  tool_payload?: Record<string, unknown> | null;
  created_at?: string | null;
}

export interface LotteryChatSendResponse {
  message: {
    id: string;
    role: string;
    content: string;
    structured_content?: {
      type?: string;
      tool?: string;
      data?: unknown;
      warnings?: { code: string; message: string }[];
      disclaimer?: string;
    } | null;
    tool_trace?: { tool: string; status: string; duration_ms: number; error_code?: string | null }[];
  };
  user_message_id: string;
  context: Record<string, unknown>;
  suggestions: string[];
  synthesis_fallback: boolean;
  latency_ms: number;
}

export interface LotterySavedQuery {
  id: string;
  name: string;
  payload: Record<string, unknown>;
  description?: string | null;
  query_type?: string | null;
  is_favorite?: boolean;
  run_count?: number;
  last_run_at?: string | null;
  tags?: string[];
  created_at?: string | null;
  updated_at?: string | null;
}

export interface LotteryDashboard {
  module_enabled: boolean;
  sync_enabled: boolean;
  lotteries_count: number;
  draws_count: number;
  numbers_count: number;
  first_draw_date?: string | null;
  last_draw_date?: string | null;
  favorites: LotteryLottery[];
  recent_queries: LotteryRecentQuery[];
  saved_queries: { id: string; name: string; query_type?: string | null; is_favorite?: boolean; run_count?: number }[];
  note?: string | null;
  disclaimer: string;
}

export interface LotteryDetail {
  lottery: LotteryLottery;
  aliases: string[];
  is_favorite: boolean;
  recent_draws: DrawResult[];
}

export interface LotteryFavorite {
  lottery_id: string;
  lottery: LotteryLottery;
  display_order: number;
  created_at?: string | null;
}

export interface LotteryRecentQuery {
  id: string;
  query_type: string;
  title: string;
  parameters: Record<string, unknown>;
  created_at?: string | null;
}

export interface LotteryPreferences {
  default_lottery_id?: string | null;
  default_date_mode: "exact" | "range";
  default_range_days: number;
  default_page_size: number;
  preferred_export_format: "csv" | "xlsx" | "pdf";
  show_source_ids: boolean;
  compact_results: boolean;
  timezone: string;
  date_format: string;
  first_day_of_week: number;
  disclaimer_acknowledged: boolean;
  onboarding_completed: boolean;
}

export interface LotteryExportResponse {
  export_id: string;
  status: string;
  filename: string;
  mime_type: string;
  size: number;
  row_count?: number | null;
  expires_at: string;
  download_url: string;
}
