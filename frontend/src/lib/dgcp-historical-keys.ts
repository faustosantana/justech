/** Stable keys for historical supplier/institution profiles (mirror backend). */

function normalizePartyName(name?: string | null): string {
  if (!name) return "";
  return name
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/,/g, " ")
    .replace(/\./g, " ")
    .replace(/\bs\.?\s*r\.?\s*l\.?\b/g, "srl")
    .replace(/\bs\.?\s*a\.?\b/g, "sa")
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function sha1Short(input: string): string {
  // Lightweight FNV-1a hex — backend uses sha1; for links we prefer RPE/code.
  let h = 0x811c9dc5;
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0).toString(16).padStart(8, "0").slice(0, 10);
}

export function supplierStableKey(opts: {
  rpe?: string | null;
  rnc?: string | null;
  name?: string | null;
}): string {
  const rnc = (opts.rnc || "").replace(/\D/g, "");
  if (rnc.length >= 9) return `rnc-${rnc}`;
  const rpe = (opts.rpe || "").replace(/[^0-9A-Za-z]/g, "");
  if (rpe) return `rpe-${rpe}`;
  const norm = normalizePartyName(opts.name);
  if (!norm) return "unknown";
  const slug = norm.replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 48) || "x";
  // Prefer sending name key that backend can parse; digest optional
  return `name-${slug}-${sha1Short(norm)}`;
}

export function institutionStableKey(opts: {
  code?: string | number | null;
  name?: string | null;
}): string {
  if (opts.code !== undefined && opts.code !== null && String(opts.code).trim()) {
    const code = String(opts.code).trim().replace(/[^0-9A-Za-z_-]/g, "");
    if (code) return `code-${code}`;
  }
  const norm = normalizePartyName(opts.name);
  if (!norm) return "unknown";
  const slug = norm.replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 48) || "x";
  return `name-${slug}-${sha1Short(norm)}`;
}

export function supplierProfileHref(opts: {
  rpe?: string | null;
  rnc?: string | null;
  name?: string | null;
  windowMonths?: number;
}): string {
  const key = encodeURIComponent(supplierStableKey(opts));
  const w = opts.windowMonths ?? 24;
  return `/dgcp/intelligence/supplier/${key}?window_months=${w}`;
}

export function institutionProfileHref(opts: {
  code?: string | number | null;
  name?: string | null;
  windowMonths?: number;
}): string {
  const key = encodeURIComponent(institutionStableKey(opts));
  const w = opts.windowMonths ?? 24;
  return `/dgcp/intelligence/institution/${key}?window_months=${w}`;
}
