export type M365DocumentItem = {
  id: string;
  name: string;
  path: string;
  source_type: string;
  source_label: string;
  mime_type?: string | null;
  size_bytes?: number | null;
  web_url?: string | null;
  download_url?: string | null;
  drive_id?: string | null;
  item_id?: string | null;
  site_id?: string | null;
  parent_item_id?: string | null;
  is_folder: boolean;
  owner_name?: string | null;
  modified_at?: string | null;
  indexed?: boolean;
  repository_id?: string | null;
};

export type M365DocumentSearchResult = {
  query?: string;
  items: M365DocumentItem[];
  total: number;
  connected: boolean;
  message: string;
  mode?: "search" | "path";
  folder_path?: string;
  suggest_open_as_folder?: boolean;
};

export type M365DocumentBrowseResult = {
  items: M365DocumentItem[];
  parent_id?: string | null;
  drive_id?: string | null;
  site_id?: string | null;
  breadcrumb: { id: string; name: string }[];
  connected: boolean;
  message: string;
};

export type M365DocumentLinkPayload = {
  company_id: string;
  field_key: string;
  item_id: string;
  representative_id?: string;
  drive_id?: string;
  source_type?: string;
  site_id?: string;
  name?: string;
  web_url?: string;
  path?: string;
  valid_until?: string;
};

export type M365DgcpLinkPayload = {
  item_id: string;
  drive_id?: string;
  source_type?: string;
  site_id?: string;
  name?: string;
  web_url?: string;
  path?: string;
};
