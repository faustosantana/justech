import { invoke } from "@tauri-apps/api/core";

export type AppConfig = {
  web_url: string;
  api_url: string;
  tenant_slug: string;
  remember_session: boolean;
  clear_on_exit: boolean;
  require_https: boolean;
  setup_completed: boolean;
};

export type SessionState = {
  configured: boolean;
  authenticated: boolean;
  web_url: string;
  api_url: string;
  tenant_slug: string;
  remember_session: boolean;
  clear_on_exit: boolean;
  require_https: boolean;
  setup_completed: boolean;
  version: string;
};

export type ConnectionTest = {
  ok: boolean;
  message: string;
  api_url: string;
  web_url: string;
};

export type AssistantMessage = {
  role: string;
  content: string;
  timestamp: string;
};

export type NotificationList = {
  items: Array<{ id: string; title: string; message: string; severity?: string }>;
  total: number;
  unread_count: number;
};

export const desktopApi = {
  getSessionState: () => invoke<SessionState>("get_session_state"),
  getAppConfig: () => invoke<AppConfig>("get_app_config"),
  saveAppConfig: (config: AppConfig) =>
    invoke<{ ok: boolean; message: string }>("save_app_config", { config }),
  testServerConnection: () => invoke<ConnectionTest>("test_server_connection"),
  completeSetup: () => invoke<SessionState>("complete_setup"),
  resetAppConfig: () => invoke<SessionState>("reset_app_config"),
  login: (email: string, password: string) =>
    invoke<SessionState>("desktop_login", { email, password }),
  logout: () => invoke<SessionState>("desktop_logout"),
  enterApp: () => invoke<SessionState>("enter_app"),
  askAssistant: (question: string) => invoke<AssistantMessage>("ask_assistant", { question }),
  getAssistantHistory: () => invoke<AssistantMessage[]>("get_assistant_history"),
  appendAssistantHistory: (user: AssistantMessage, assistant: AssistantMessage) =>
    invoke("append_assistant_history", { user, assistant }),
  getNotifications: () => invoke<NotificationList>("get_notifications"),
  captureAndUpload: () => invoke<{ document_id: string; title: string }>("capture_and_upload"),
  openServerPath: (path: string) => invoke("open_server_path", { path }),
};
