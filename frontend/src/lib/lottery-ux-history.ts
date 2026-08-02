/** Local query history / favorites / shared links for Lottery IA UX. */

export type SavedUxQuery = {
  id: string;
  text: string;
  favorite: boolean;
  shared: boolean;
  createdAt: string;
  lastRunAt: string;
};

const KEY = "lottery-ia-ux-history-v1";

function read(): SavedUxQuery[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as SavedUxQuery[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function write(items: SavedUxQuery[]) {
  if (typeof window === "undefined") return;
  localStorage.setItem(KEY, JSON.stringify(items.slice(0, 80)));
}

export function listUxHistory(): SavedUxQuery[] {
  return read().sort((a, b) => b.lastRunAt.localeCompare(a.lastRunAt));
}

export function listUxFavorites(): SavedUxQuery[] {
  return listUxHistory().filter((x) => x.favorite);
}

export function listUxShared(): SavedUxQuery[] {
  return listUxHistory().filter((x) => x.shared);
}

export function rememberUxQuery(text: string): SavedUxQuery {
  const trimmed = text.trim();
  const now = new Date().toISOString();
  const items = read();
  const existing = items.find((x) => x.text === trimmed);
  if (existing) {
    existing.lastRunAt = now;
    write(items);
    return existing;
  }
  const row: SavedUxQuery = {
    id: `q-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    text: trimmed,
    favorite: false,
    shared: false,
    createdAt: now,
    lastRunAt: now,
  };
  write([row, ...items]);
  return row;
}

export function saveUxQuery(text: string, opts?: { favorite?: boolean; shared?: boolean }): SavedUxQuery {
  const row = rememberUxQuery(text);
  const items = read();
  const hit = items.find((x) => x.id === row.id);
  if (hit) {
    if (opts?.favorite != null) hit.favorite = opts.favorite;
    else hit.favorite = true;
    if (opts?.shared != null) hit.shared = opts.shared;
    hit.lastRunAt = new Date().toISOString();
    write(items);
    return hit;
  }
  return row;
}

export function toggleUxFavorite(id: string): SavedUxQuery | null {
  const items = read();
  const hit = items.find((x) => x.id === id);
  if (!hit) return null;
  hit.favorite = !hit.favorite;
  write(items);
  return hit;
}

export function markUxShared(id: string): SavedUxQuery | null {
  const items = read();
  const hit = items.find((x) => x.id === id);
  if (!hit) return null;
  hit.shared = true;
  write(items);
  return hit;
}

export function removeUxHistory(id: string) {
  write(read().filter((x) => x.id !== id));
}
