export type ChannelStatus = {
  channel: string;
  label: string;
  status: string;
  detail?: string | null;
  route?: string | null;
};

export type CommunicationsHubStatus = {
  outlook: ChannelStatus;
  whatsapp: ChannelStatus;
  teams: ChannelStatus;
  contacts: ChannelStatus;
  search: ChannelStatus;
  ai: ChannelStatus;
};

export type WhatsappSession = {
  id: string;
  label: string;
  account_type: string;
  connection_status: string;
  phone_number?: string | null;
  push_name?: string | null;
  qr_image?: string | null;
  last_error?: string | null;
  connected_at?: string | null;
  created_at: string;
};

export type WhatsappSessionLimits = {
  plan: string;
  limit: number;
  active_count: number;
  can_create: boolean;
};

export type WhatsappChat = {
  id: string;
  session_id?: string | null;
  remote_jid: string;
  name?: string | null;
  phone_number?: string | null;
  profile_picture_url?: string | null;
  is_group: boolean;
  is_favorite?: boolean;
  unread_count: number;
  last_message_preview?: string | null;
  last_message_at?: string | null;
  labels: string[];
  contact_type?: string | null;
  related_company_id?: string | null;
  related_company_name?: string | null;
  ai_classification?: string | null;
  ai_classification_label?: string | null;
  ai_priority?: number | null;
};

export type WhatsappContextPreview = {
  chat_id: string;
  contact_name: string;
  phone_number?: string | null;
  is_group: boolean;
  company_name?: string | null;
  related_company_id?: string | null;
  classification?: string | null;
  classification_label?: string | null;
  summary?: string | null;
  suggested_reply?: string | null;
  entities: Record<string, unknown>;
  matched_contact_id?: string | null;
  opportunities: Array<Record<string, unknown>>;
  quotes: Array<Record<string, unknown>>;
  sales: Array<Record<string, unknown>>;
  emails: Array<Record<string, unknown>>;
  documents: Array<Record<string, unknown>>;
  price_history: Array<Record<string, unknown>>;
  recommendations: string[];
  deep_search_available: boolean;
};

export type WhatsappDeepContext = {
  chat_id: string;
  contact_name: string;
  company_name?: string | null;
  query_used: string;
  sales: Array<Record<string, unknown>>;
  quotes: Array<Record<string, unknown>>;
  prices: Array<Record<string, unknown>>;
  emails: Array<Record<string, unknown>>;
  documents: Array<Record<string, unknown>>;
  opportunities: Array<Record<string, unknown>>;
  recommendation: string;
  summary: string;
};

export type WhatsappSyncResult = {
  status: string;
  chats_synced: number;
  contacts_synced: number;
  message: string;
};

export type ConversationFilter = "all" | "unread" | "favorites" | "groups" | "clients" | "suppliers";

export type WhatsappChatIntelligence = {
  chat_id: string;
  classification?: string | null;
  classification_label?: string | null;
  confidence?: number | null;
  priority?: number | null;
  sentiment?: string | null;
  summary?: string | null;
  suggested_reply?: string | null;
  entities: Record<string, unknown>;
  secondary_labels: string[];
  suggested_actions: string[];
  last_analyzed_at?: string | null;
};

export type WhatsappIntelligenceLink = {
  label: string;
  url: string;
  type: string;
};

export type WhatsappMessage = {
  id: string;
  wa_message_id: string;
  remote_jid: string;
  from_me: boolean;
  body?: string | null;
  media_type?: string | null;
  media_mime?: string | null;
  content_type?: string | null;
  quoted_wa_message_id?: string | null;
  wa_timestamp_ms?: number | null;
  created_at: string;
};

export type WhatsappAiActionResponse = {
  action: string;
  result: string;
  suggestions: string[];
  classification?: string | null;
  priority?: number | null;
  links?: WhatsappIntelligenceLink[];
  created_id?: string | null;
  suggested_reply?: string | null;
};

export type HubTab = "outlook" | "whatsapp" | "teams" | "contactos" | "historial" | "ia";

export type HubChannelFilter = "all" | "whatsapp" | "outlook" | "teams" | "enterprise" | "documents";

export type CommunicationsTimelineItem = {
  id: string;
  channel: string;
  title: string;
  subtitle?: string | null;
  preview?: string | null;
  timestamp?: string | null;
  url: string;
  score: number;
  metadata?: Record<string, unknown>;
};

export type CommunicationsUnifiedSearchResult = {
  query: string;
  total: number;
  groups: import("./search").SearchResultGroup[];
  timeline: CommunicationsTimelineItem[];
  sources_searched: string[];
  latency_ms?: number | null;
};

export type UnifiedContact = {
  id: string;
  display_name: string;
  company_name?: string | null;
  primary_email?: string | null;
  primary_phone?: string | null;
  sources: string[];
  source_labels: string[];
  tags: string[];
  last_activity_at?: string | null;
  synced_at?: string | null;
};

export type UnifiedContactIdentity = {
  id: string;
  source: string;
  external_id: string;
  display_name?: string | null;
  email?: string | null;
  phone?: string | null;
  company_name?: string | null;
  profile_url?: string | null;
};

export type UnifiedContactStats = {
  whatsapp_chats: number;
  whatsapp_messages: number;
  tasks: number;
  dgcp_opportunities: number;
  linked_sources: number;
};

export type UnifiedContactProfile360 = {
  contact: UnifiedContact;
  identities: UnifiedContactIdentity[];
  emails: string[];
  phones: string[];
  stats: UnifiedContactStats;
  timeline: CommunicationsTimelineItem[];
  search_groups: import("./search").SearchResultGroup[];
  odoo_summary?: Record<string, unknown> | null;
  dgcp_opportunities: Array<Record<string, string>>;
};

export type CommunicationsRepositoryItem = {
  id: string;
  source: string;
  source_label: string;
  name: string;
  category: string;
  category_label: string;
  mime_type?: string | null;
  size_bytes?: number | null;
  web_url?: string | null;
  graph_item_id?: string | null;
};

export type CommunicationsRepositoryList = {
  items: CommunicationsRepositoryItem[];
  total: number;
  categories: Record<string, number>;
  sources: string[];
};

export type CommunicationsAttachAction = {
  ok: boolean;
  channel: string;
  message: string;
  filename?: string | null;
  message_id?: string | null;
  web_url?: string | null;
};
