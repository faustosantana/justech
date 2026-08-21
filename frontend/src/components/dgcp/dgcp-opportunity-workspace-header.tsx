"use client";

import { ArrowLeft, ExternalLink, MoreHorizontal } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { MutateButton } from "@/components/permissions/mutate-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { PlatformAccess } from "@/lib/admin";
import {
  ACTION_LABELS,
  funnelLabelsRedundant,
  resolveOpportunityGuidance,
} from "@/lib/dgcp-funnel";
import {
  COMPANY_LABELS,
  formatDate,
  type DGCPOpportunity,
  type OpportunityAction,
} from "@/lib/dgcp";
import { cn } from "@/lib/utils";

type Props = {
  opportunity: DGCPOpportunity;
  access: PlatformAccess | null;
  updating?: boolean;
  onAction: (action: OpportunityAction) => void;
  backHref?: string;
  backLabel?: string;
};

export function DgcpOpportunityWorkspaceHeader({
  opportunity,
  access,
  updating,
  onAction,
  backHref = "/apps/licitaciones/mis-licitaciones",
  backLabel = "Mis Licitaciones",
}: Props) {
  const guidance = resolveOpportunityGuidance(opportunity);
  const [moreOpen, setMoreOpen] = useState(false);
  const secondaryActions = guidance.availableActions.filter(
    (a) => a !== guidance.primaryAction && a !== "descartar",
  );
  const canDiscard = guidance.availableActions.includes("descartar");
  const moreActions = [
    ...secondaryActions,
    ...(canDiscard ? (["descartar"] as OpportunityAction[]) : []),
  ];

  const responsible =
    opportunity.responsible_name ||
    (typeof opportunity.full_info?.responsible_name === "string"
      ? opportunity.full_info.responsible_name
      : null);

  return (
    <header className="space-y-2">
      <Button variant="ghost" size="sm" className="-ml-2 h-7 px-2 text-muted-foreground" asChild>
        <Link href={backHref}>
          <ArrowLeft className="mr-1.5 h-3.5 w-3.5" />
          {backLabel}
        </Link>
      </Button>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="font-mono text-xs font-medium text-primary sm:text-sm">{opportunity.code}</p>
          <h1 className="text-base font-semibold leading-snug tracking-tight text-foreground sm:text-lg">
            {opportunity.title}
          </h1>
          <p className="mt-0.5 truncate text-xs text-muted-foreground sm:text-sm">
            {opportunity.institution}
          </p>
        </div>

        <div className="flex max-w-full flex-wrap items-center justify-end gap-1.5">
          <Badge variant="muted" className="text-[10px] sm:text-xs">
            {COMPANY_LABELS[opportunity.company] || opportunity.company}
          </Badge>
          <Badge variant="default" className="text-[10px] sm:text-xs">
            {guidance.funnelStageLabel}
          </Badge>
          {!funnelLabelsRedundant(guidance.funnelStageLabel, guidance.statusLabel) ? (
            <Badge variant="outline" className="text-[10px] sm:text-xs">
              {guidance.statusLabel}
            </Badge>
          ) : null}
          {(opportunity as DGCPOpportunity & { needs_review?: boolean }).needs_review ? (
            <Badge variant="warning" className="text-[10px] sm:text-xs">
              Revisión
            </Badge>
          ) : null}
          {opportunity.deadline ? (
            <span className="rounded-md border px-2 py-0.5 text-[10px] text-muted-foreground sm:text-xs">
              Vence {formatDate(opportunity.deadline)}
            </span>
          ) : null}
          {responsible ? (
            <span className="rounded-md border px-2 py-0.5 text-[10px] text-muted-foreground sm:text-xs">
              {responsible}
            </span>
          ) : null}
          {opportunity.confidence_score > 0 ? (
            <span className="rounded-md border px-2 py-0.5 text-[10px] text-muted-foreground sm:text-xs">
              {opportunity.confidence_score}% IA
            </span>
          ) : null}
          {opportunity.source_url ? (
            <Button variant="outline" size="sm" className="h-7 px-2 text-xs" asChild>
              <a href={opportunity.source_url} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="mr-1 h-3 w-3" />
                DGCP
              </a>
            </Button>
          ) : null}
          {moreActions.length > 0 ? (
            <div className="relative">
              <Button
                type="button"
                size="sm"
                variant="ghost"
                className="h-7 w-7 px-0"
                disabled={updating}
                onClick={() => setMoreOpen((v) => !v)}
                aria-label="Más acciones"
              >
                <MoreHorizontal className="h-4 w-4" />
              </Button>
              {moreOpen ? (
                <div className="absolute right-0 z-30 mt-1 min-w-[200px] rounded-md border bg-background p-1 shadow-md">
                  {moreActions.map((action) => (
                    <button
                      key={action}
                      type="button"
                      className="block w-full rounded px-3 py-1.5 text-left text-sm hover:bg-muted"
                      onClick={() => {
                        setMoreOpen(false);
                        onAction(action);
                      }}
                    >
                      {ACTION_LABELS[action]}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>

      {(guidance.nextAction || guidance.primaryAction) && (
        <div
          className={cn(
            "flex flex-wrap items-center gap-2 rounded-md border border-border/80 bg-muted/40 px-3 py-2",
          )}
        >
          <div className="min-w-0 flex-1 text-xs sm:text-sm">
            <span className="font-medium text-foreground">Siguiente: </span>
            <span className="text-muted-foreground">{guidance.nextAction || "—"}</span>
          </div>
          {guidance.primaryAction ? (
            <MutateButton
              permission="mutate_dgcp"
              access={access}
              size="sm"
              className="h-7 shrink-0"
              disabled={updating}
              onClick={() => onAction(guidance.primaryAction!)}
            >
              {ACTION_LABELS[guidance.primaryAction]}
            </MutateButton>
          ) : null}
        </div>
      )}
    </header>
  );
}
