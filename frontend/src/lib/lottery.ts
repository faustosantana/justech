/** Tipos y helpers del módulo Lottery IA Control Center. */

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

export interface LotteryDashboardConfig {
  lottery_ids: string[];
  disabled_ids: string[];
  recent_draws: number;
  show_primera: boolean;
  show_segunda: boolean;
  show_tercera: boolean;
}

export const DEFAULT_DASHBOARD_CONFIG: LotteryDashboardConfig = {
  lottery_ids: [],
  disabled_ids: [],
  recent_draws: 1,
  show_primera: true,
  show_segunda: true,
  show_tercera: true,
};

/** Nombres de producto de las siete loterías activas (orden de Inicio). */
export const PRODUCT_SEVEN_LOTTERY_NAMES = [
  "Gana Más",
  "Lotería Nacional",
  "New York 10:30",
  "New York 2:30",
  "Quiniela Leidsa",
  "Quiniela Loteka",
  "Quiniela Real",
] as const;

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
  /** Cuando pregunte por un número sin indicar posición */
  default_number_position_scope?:
    | "first_position"
    | "any_position"
    | "specific_position"
    | "ask_each_time";
  default_primary_position?: number;
  dashboard?: LotteryDashboardConfig;
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

/** Tarjeta del catálogo Lottery 3.0. */
export interface LotteryCatalogCard {
  id: string;
  slug: string;
  name: string;
  commercial_name?: string | null;
  short_name?: string | null;
  country?: string | null;
  country_code?: string | null;
  flag_emoji?: string | null;
  timezone?: string | null;
  logo_url?: string | null;
  icon_key?: string | null;
  is_featured: boolean;
  is_favorite: boolean;
  draw_count: number;
  last_draw_date?: string | null;
  last_numbers: string[];
  last_sync_at?: string | null;
  next_draw_estimated_at?: string | null;
  draw_times?: string | null;
  health_status: string;
  is_searchable: boolean;
  is_comparable: boolean;
  is_ai_enabled: boolean;
  is_sync_enabled?: boolean;
}

export interface LotteryCatalogResponse {
  items: LotteryCatalogCard[];
  total: number;
  page: number;
  page_size: number;
}

export interface LotteryLatestResult {
  lottery: string;
  slug: string;
  date: string | null;
  numbers: string[];
}

export interface LotteryNumberStat {
  number: string;
  count: number;
}

export interface LotteryDashboardV2 {
  lotteries_active: number;
  lotteries_visible: number;
  lotteries_synced: number;
  results_today: number;
  draws_historical: number;
  numbers_stored: number;
  last_update_at?: string | null;
  sources_healthy: number;
  sources_error: number;
  latest_results: LotteryLatestResult[];
  featured: LotteryCatalogCard[];
  favorites: LotteryCatalogCard[];
  top_numbers: LotteryNumberStat[];
  bottom_numbers: LotteryNumberStat[];
  recent_queries: Record<string, unknown>[];
  sync_summary: Record<string, unknown>;
  coverage: Record<string, unknown>;
  disclaimer: string;
}

/** Executive ops dashboard — Lottery 3.0 */
export interface LotteryDashboardV3 extends LotteryDashboardV2 {
  local_today?: string | null;
  timezone?: string;
  pending_results?: number;
  expected_today?: number;
  pending_sync_enabled?: number;
  pending_visible?: number;
  last_sync_at?: string | null;
  next_sync_at?: string | null;
  worker_status?: Record<string, unknown>;
  recent_sync_runs?: Record<string, unknown>[];
  next_sync_windows?: Record<string, unknown>[];
  circuit_breakers?: Record<string, unknown>[];
  source_health?: Record<string, unknown>[];
  kpis?: Record<string, unknown>;
  results_today_note?: string;
  backup_gate?: Record<string, unknown>;
  operational_alerts?: Record<string, unknown>[];
}

/** Lotería administrable (Lottery 2.0). */
export interface LotteryAdminLottery {
  id: string;
  source_id: number;
  name: string;
  commercial_name?: string | null;
  short_name?: string | null;
  normalized_name: string;
  slug: string;
  country?: string | null;
  timezone: string;
  currency?: string | null;
  active: boolean;
  is_loto: boolean;
  is_aggregate: boolean;
  is_visible: boolean;
  is_visible_dashboard: boolean;
  is_visible_catalog: boolean;
  is_searchable: boolean;
  is_ai_enabled: boolean;
  is_comparable: boolean;
  is_sync_enabled: boolean;
  is_auto_write_enabled: boolean;
  is_featured: boolean;
  display_order: number;
  logo_url?: string | null;
  icon_key?: string | null;
  data_source?: string | null;
  adapter_key?: string | null;
  external_id?: string | null;
  draw_schedule_cron?: string | null;
  draw_days?: string | null;
  draw_times?: string | null;
  sync_interval_minutes?: number | null;
  sync_post_draw_delay_minutes?: number | null;
  sync_max_retries?: number | null;
  sync_active_hours?: string | null;
  last_sync_at?: string | null;
  last_result_at?: string | null;
  next_draw_estimated_at?: string | null;
  health_status: string;
  last_error?: string | null;
  draw_count: number;
  numbers_count: number;
  first_draw_date?: string | null;
  last_draw_date?: string | null;
  admin_notes?: string | null;
}

export type LotteryAdminBulkAction =
  | "enable"
  | "disable"
  | "show"
  | "hide"
  | "allow_search"
  | "block_search"
  | "enable_ai"
  | "disable_ai"
  | "enable_sync"
  | "disable_sync"
  | "enable_auto_write"
  | "disable_auto_write"
  | "feature"
  | "unfeature"
  | "set_order";

export interface LotteryAdminBulkResponse {
  updated: number;
  action: string;
}

const LOTTERY_ADMIN_ROLES = new Set(["owner", "admin", "superadmin"]);

const LOTTERY_ADMIN_PERMISSIONS = new Set([
  "lottery.admin",
  "lottery_admin_lotteries",
  "lottery_admin_ai",
  "lottery_admin_prompts",
  "lottery_admin_models",
  "lottery_admin_tools",
  "lottery_admin_safety",
]);

export function canAccessLotteryAdmin(
  role: string | null,
  permissions?: string[] | null,
): boolean {
  if (!role) return false;
  const r = role.toLowerCase();
  if (LOTTERY_ADMIN_ROLES.has(r)) return true;
  if (r === "lottery_admin_ai") return true;
  if (!permissions?.length) return false;
  return permissions.some((p) => LOTTERY_ADMIN_PERMISSIONS.has(p));
}

export function healthStatusLabel(status: string): string {
  switch (status) {
    case "healthy":
      return "Saludable";
    case "error":
      return "Error";
    case "degraded":
      return "Degradado";
    default:
      return "Desconocido";
  }
}
