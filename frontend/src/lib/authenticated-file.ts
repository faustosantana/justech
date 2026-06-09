/**
 * Descarga/visualización autenticada de archivos vía Bearer (sin tokens en URL).
 */

import {
  ApiError,
  redirectToLogin,
} from "@/lib/api";
import { getAccessToken, getTenantId } from "@/lib/auth";

function getApiUrl(): string {
  const fallback = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
  if (typeof window === "undefined") return fallback;
  return `${window.location.origin}/api/v1`;
}

/** Normaliza rutas absolutas o con prefijo /api/v1 al path relativo de la API. */
export function normalizeApiPath(path: string): string {
  if (!path) return path;
  if (path.startsWith("http://") || path.startsWith("https://")) {
    const url = new URL(path);
    const pathname = url.pathname.replace(/^\/api\/v1/, "");
    return `${pathname}${url.search}`;
  }
  if (path.startsWith("/api/v1")) return path.slice("/api/v1".length) || "/";
  return path.startsWith("/") ? path : `/${path}`;
}

function parseFilename(contentDisposition: string | null, fallback: string): string {
  if (!contentDisposition) return fallback;
  const star = /filename\*=UTF-8''([^;]+)/i.exec(contentDisposition);
  if (star?.[1]) {
    try {
      return decodeURIComponent(star[1]);
    } catch {
      return star[1];
    }
  }
  const plain = /filename="?([^";]+)"?/i.exec(contentDisposition);
  return plain?.[1] ?? fallback;
}

export interface AuthenticatedFilePayload {
  blob: Blob;
  objectUrl: string;
  contentType: string;
  filename: string;
}

let refreshInFlight: Promise<boolean> | null = null;

async function tryRefreshAccessToken(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;
  const { getRefreshToken, setAuthTokens } = await import("@/lib/auth");
  refreshInFlight = (async () => {
    const refresh = getRefreshToken();
    if (!refresh) return false;
    try {
      const response = await fetch(`${getApiUrl()}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!response.ok) return false;
      const tokens = (await response.json()) as import("@/lib/auth").AuthTokens;
      setAuthTokens(tokens);
      return true;
    } catch {
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

export async function fetchAuthenticatedFile(
  path: string,
  retried = false,
): Promise<AuthenticatedFilePayload> {
  const apiPath = normalizeApiPath(path);
  const token = getAccessToken();
  const tenantId = getTenantId();

  if (!token) {
    redirectToLogin(true);
    throw new Error("UNAUTHORIZED");
  }

  const response = await fetch(`${getApiUrl()}${apiPath}`, {
    headers: {
      Authorization: `Bearer ${token}`,
      ...(tenantId ? { "X-Tenant-ID": tenantId } : {}),
    },
  });

  if (response.status === 401 && !retried) {
    const refreshed = await tryRefreshAccessToken();
    if (refreshed) return fetchAuthenticatedFile(path, true);
    redirectToLogin(true);
    throw new Error("UNAUTHORIZED");
  }

  if (response.status === 401) {
    throw new Error("UNAUTHORIZED");
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: string; message?: string };
    throw new ApiError(
      response.status,
      "FILE_FETCH_ERROR",
      body.detail ?? body.message ?? `Error al obtener archivo (${response.status})`,
    );
  }

  const blob = await response.blob();
  const contentType = response.headers.get("Content-Type") ?? blob.type ?? "application/octet-stream";
  const filename = parseFilename(response.headers.get("Content-Disposition"), "documento");
  const objectUrl = URL.createObjectURL(blob);

  return { blob, objectUrl, contentType, filename };
}

export function revokeAuthenticatedFileUrl(objectUrl: string | null | undefined): void {
  if (objectUrl) URL.revokeObjectURL(objectUrl);
}

export function downloadAuthenticatedBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  revokeAuthenticatedFileUrl(url);
}

export function openAuthenticatedBlobInNewTab(objectUrl: string): void {
  window.open(objectUrl, "_blank", "noopener,noreferrer");
}

export function isPdfContent(contentType: string, filename: string): boolean {
  return contentType.includes("pdf") || filename.toLowerCase().endsWith(".pdf");
}
