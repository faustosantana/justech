import { apiClient, ApiError } from "@/lib/api";
import type { DGCPOpportunity, OpportunityAction, OpportunityStatus } from "@/lib/dgcp";

/** Estado esperado tras cada acción del embudo (canónico backend). */
const ACTION_TARGET_STATUS: Partial<Record<OpportunityAction, OpportunityStatus>> = {
  marcar_interes: "interested",
  mostrar_interes: "interested",
  desmarcar_interes: "detected",
  revisar: "detected",
  iniciar_preparacion: "preparing",
  licitar: "preparing",
  marcar_listo_presentar: "ready_to_submit",
  marcar_presentada: "submitted",
  marcar_suspendida: "suspended",
  marcar_adjudicada: "awarded",
  ganada: "awarded",
  marcar_no_adjudicada: "lost",
  perdida: "lost",
  descartar: "discarded",
};

const RECONCILE_POLL_MS = 2_000;
const RECONCILE_MAX_POLLS = 20;

function shouldReconcile(err: unknown): boolean {
  if (err instanceof ApiError) {
    return err.status === 408 || err.status === 502 || err.status === 504 || err.status === 503;
  }
  if (err instanceof Error) {
    return err.name === "AbortError" || /fetch|network|timeout/i.test(err.message);
  }
  return false;
}

function statusMatchesExpected(current: string, expected: OpportunityStatus): boolean {
  if (current === expected) return true;
  if (expected === "preparing" && (current === "preparing" || current === "to_bid")) return true;
  if (expected === "awarded" && (current === "awarded" || current === "won")) return true;
  if (expected === "submitted" && (current === "submitted" || current === "under_evaluation")) {
    return true;
  }
  return false;
}

async function pollOpportunityUntil(
  opportunityId: string,
  expected: OpportunityStatus,
): Promise<DGCPOpportunity | null> {
  for (let i = 0; i < RECONCILE_MAX_POLLS; i += 1) {
    await new Promise((r) => setTimeout(r, RECONCILE_POLL_MS));
    try {
      const opp = await apiClient.getDGCPOpportunity(opportunityId);
      if (statusMatchesExpected(opp.status, expected)) return opp;
    } catch {
      /* sigue intentando */
    }
  }
  return null;
}

export type ApplyDGCPOpportunityActionResult = {
  opportunity: DGCPOpportunity;
  reconciled: boolean;
};

/**
 * Ejecuta una acción del embudo y, si la red corta la respuesta,
 * reconcilia el estado real consultando el proceso.
 */
export async function applyDGCPOpportunityAction(
  opportunityId: string,
  action: OpportunityAction,
  notes?: string,
): Promise<ApplyDGCPOpportunityActionResult> {
  const expected = ACTION_TARGET_STATUS[action];
  try {
    const opportunity = await apiClient.applyDGCPAction(opportunityId, action, notes);
    return { opportunity, reconciled: false };
  } catch (err) {
    if (!expected || !shouldReconcile(err)) throw err;
    const opportunity = await pollOpportunityUntil(opportunityId, expected);
    if (opportunity) return { opportunity, reconciled: true };
    throw err;
  }
}
