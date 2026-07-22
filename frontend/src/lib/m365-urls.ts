/** URLs Microsoft 365 Business — nunca usar dominios consumer (live.com). */

const CONSUMER_HOSTS = ["onedrive.live.com", "login.live.com", "outlook.live.com"];

const DEFAULT_SHAREPOINT_HOST =
  process.env.NEXT_PUBLIC_M365_SHAREPOINT_HOST ??
  process.env.NEXT_PUBLIC_M365_TENANT_SHAREPOINT_HOST ??
  "justechdo-my.sharepoint.com";

export function getM365SharePointHost(): string {
  const fromEnv = process.env.NEXT_PUBLIC_M365_SHAREPOINT_HOST?.trim();
  if (fromEnv) {
    return fromEnv.replace(/^https?:\/\//, "").replace(/\/$/, "");
  }
  return DEFAULT_SHAREPOINT_HOST;
}

export function isConsumerMicrosoftUrl(url: string): boolean {
  try {
    const host = new URL(url).hostname.toLowerCase();
    return CONSUMER_HOSTS.some((h) => host === h || host.endsWith(`.${h}`));
  } catch {
    return false;
  }
}

/** URL segura para abrir en navegador; null si es dominio consumer. */
export function sanitizeMicrosoftUrl(url: string | null | undefined): string | null {
  if (!url?.trim()) return null;
  if (isConsumerMicrosoftUrl(url)) return null;
  return url;
}

/** Búsqueda en OneDrive Business (SharePoint host) — solo fallback externo. */
export function buildSharePointOneDriveSearchUrl(query: string): string {
  const host = getM365SharePointHost();
  return `https://${host}/_layouts/15/onedrive.aspx?view=7&q=${encodeURIComponent(query)}`;
}
