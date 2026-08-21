/** Mensajes de API seguros para UI (sin TypeError / nombres de función). */

export function isTechnicalErrorMessage(raw: string): boolean {
  const t = (raw || "").trim();
  if (!t) return true;
  if (
    /is not a function|TypeError|ReferenceError|undefined is not|Cannot read|ECONN|NetworkError|Failed to fetch/i.test(
      t,
    )
  ) {
    return true;
  }
  if (/Inconsistencia de métricas|stack|at Object\.|\.tsx?:\d+/i.test(t)) return true;
  if (/^[a-zA-Z0-9_.$]+\.[a-zA-Z0-9_.$]+/.test(t) && t.length < 80) return true;
  if (t.includes("\n") || t.length > 280) return true;
  return false;
}

export function userFacingApiError(err: unknown, fallback: string): string {
  const raw =
    err && typeof err === "object" && "message" in err && typeof (err as Error).message === "string"
      ? (err as Error).message
      : "";
  if (!raw || raw === "UNAUTHORIZED") return fallback;
  if (isTechnicalErrorMessage(raw)) return fallback;
  return raw;
}

export type ExpedienteBlocker = {
  id: string;
  label: string;
  kind: "missing" | "review" | "expired" | "complete_form" | "other";
};

export type ExpedienteReadiness = {
  canPrepare: boolean;
  incomplete: boolean;
  blockers: ExpedienteBlocker[];
  summary: string;
  counts: {
    total: number;
    compliant: number;
    missing: number;
    expired: number;
    toComplete: number;
    review: number;
    otherOpen: number;
  };
};

type BidLike = {
  total_requirements?: number | null;
  mandatory_requirements?: number | null;
  compliant_count?: number | null;
  found_documents?: number | null;
  pending_documents?: number | null;
  expired_documents?: number | null;
  forms_to_complete?: number | null;
  review_count?: number | null;
  missing?: string[];
  expired?: string[];
  to_complete?: string[];
  requires_review?: string[];
  recommended_tasks?: string[];
};

/**
 * Interpreta el estado operativo del bid-package para explicar al usuario
 * qué falta, sin forzar que los contadores “cuadran” artificialmente.
 */
export function buildExpedienteReadiness(bid: BidLike | null | undefined): ExpedienteReadiness {
  if (!bid) {
    return {
      canPrepare: false,
      incomplete: true,
      blockers: [{ id: "no-analysis", label: "Ejecute el análisis de requisitos primero", kind: "other" }],
      summary: "Sin análisis de requisitos.",
      counts: { total: 0, compliant: 0, missing: 0, expired: 0, toComplete: 0, review: 0, otherOpen: 0 },
    };
  }

  const total = Number(bid.total_requirements ?? bid.mandatory_requirements ?? 0);
  const compliant = Number(bid.compliant_count ?? 0);
  const missingList = bid.missing || [];
  const expiredList = bid.expired || [];
  const toCompleteList = bid.to_complete || [];
  const reviewList = bid.requires_review || [];
  const missing = missingList.length || Number(bid.pending_documents ?? 0);
  const expired = expiredList.length || Number(bid.expired_documents ?? 0);
  const toComplete = toCompleteList.length || Number(bid.forms_to_complete ?? 0);
  const review = reviewList.length || Number(bid.review_count ?? 0);

  const accounted = compliant + missing + expired + toComplete + review;
  const otherOpen = Math.max(0, total - accounted);

  const blockers: ExpedienteBlocker[] = [];
  for (const name of missingList) {
    blockers.push({ id: `m:${name}`, label: name, kind: "missing" });
  }
  for (const name of expiredList) {
    blockers.push({ id: `e:${name}`, label: `${name} (vencido)`, kind: "expired" });
  }
  for (const name of toCompleteList) {
    blockers.push({ id: `c:${name}`, label: `${name} (por completar / confirmar lectura)`, kind: "complete_form" });
  }
  for (const name of reviewList) {
    blockers.push({ id: `r:${name}`, label: `${name} (requiere revisión / vigencia)`, kind: "review" });
  }
  if (otherOpen > 0 && blockers.length < total) {
    blockers.push({
      id: "other-open",
      label: `${otherOpen} requisito(s) en otro estado (p. ej. disponible sin validar o no aplicable pendiente)`,
      kind: "other",
    });
  }

  const incomplete = missing + expired + toComplete + review + otherOpen > 0 || compliant < total;
  // Backend permite preparar con observaciones; canPrepare=true si hay análisis.
  const canPrepare = total > 0 || Boolean(bid.recommended_tasks?.length);

  const parts: string[] = [];
  if (missing) parts.push(`${missing} faltante(s)`);
  if (expired) parts.push(`${expired} vencido(s)`);
  if (toComplete) parts.push(`${toComplete} por completar`);
  if (review) parts.push(`${review} en revisión / vigencia`);
  if (otherOpen) parts.push(`${otherOpen} en otro estado`);

  return {
    canPrepare,
    incomplete,
    blockers,
    summary: incomplete
      ? `Expediente incompleto: ${compliant}/${total || "—"} cumplidos` +
        (parts.length ? ` · ${parts.join(" · ")}` : "")
      : `Expediente completo: ${compliant}/${total} requisitos cumplidos`,
    counts: { total, compliant, missing, expired, toComplete, review, otherOpen },
  };
}
