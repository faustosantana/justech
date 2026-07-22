"use client";

import { Calendar, User } from "lucide-react";

import { MutateButton } from "@/components/permissions/mutate-button";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { PlatformAccess } from "@/hooks/use-platform-access";
import {
  ACTION_LABELS,
  FUNNEL_STAGES,
  FUNNEL_STAGE_LABELS,
  funnelLabelsRedundant,
  resolveOpportunityGuidance,
  type FunnelStage,
} from "@/lib/dgcp-funnel";
import { formatDate, type DGCPOpportunity, type OpportunityAction } from "@/lib/dgcp";
import { cn } from "@/lib/utils";

interface Props {
  opportunity: DGCPOpportunity;
  access: PlatformAccess;
  updating?: boolean;
  onAction: (action: OpportunityAction) => void;
  variant?: "header" | "card";
}

export function DgcpFunnelHeader({ opportunity, access, updating, onAction, variant = "header" }: Props) {
  const guidance = resolveOpportunityGuidance(opportunity);
  const secondaryActions = guidance.availableActions.filter(
    (a) => a !== guidance.primaryAction && a !== "descartar",
  );
  const canDiscard = guidance.availableActions.includes("descartar");

  const inner = (
    <div className={cn("space-y-3", variant === "header" && "w-full")}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="default">{guidance.funnelStageLabel}</Badge>
        {!funnelLabelsRedundant(guidance.funnelStageLabel, guidance.statusLabel) ? (
          <Badge variant="outline">{guidance.statusLabel}</Badge>
        ) : null}
        {opportunity.needs_review ? (
          <Badge variant="warning">Requiere revisión</Badge>
        ) : null}
      </div>

      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4 text-sm">
        <div className="flex items-center gap-2 text-muted-foreground">
          <Calendar className="h-4 w-4 shrink-0" />
          <span>
            Fecha límite: <strong className="text-foreground">{formatDate(opportunity.deadline)}</strong>
          </span>
        </div>
        {opportunity.responsible_name ? (
          <div className="flex items-center gap-2 text-muted-foreground">
            <User className="h-4 w-4 shrink-0" />
            <span>
              Responsable: <strong className="text-foreground">{opportunity.responsible_name}</strong>
            </span>
          </div>
        ) : null}
      </div>

      {guidance.nextAction ? (
        <p className="text-sm text-muted-foreground rounded-lg border bg-muted/30 px-3 py-2">
          <span className="font-medium text-foreground">Siguiente paso: </span>
          {guidance.nextAction}
        </p>
      ) : null}

      <div className="flex flex-wrap gap-2">
        {guidance.primaryAction ? (
          <MutateButton
            permission="mutate_dgcp"
            access={access}
            size="sm"
            disabled={updating}
            onClick={() => onAction(guidance.primaryAction!)}
          >
            {ACTION_LABELS[guidance.primaryAction]}
          </MutateButton>
        ) : null}
        {secondaryActions.map((action) => (
          <MutateButton
            key={action}
            permission="mutate_dgcp"
            access={access}
            size="sm"
            variant="secondary"
            disabled={updating}
            onClick={() => onAction(action)}
          >
            {ACTION_LABELS[action]}
          </MutateButton>
        ))}
        {canDiscard ? (
          <MutateButton
            permission="mutate_dgcp"
            access={access}
            size="sm"
            variant="outline"
            disabled={updating}
            onClick={() => onAction("descartar")}
          >
            {ACTION_LABELS.descartar}
          </MutateButton>
        ) : null}
      </div>
    </div>
  );

  if (variant === "card") {
    return (
      <Card className="border-primary/25 bg-primary/5">
        <CardContent className="pt-6">{inner}</CardContent>
      </Card>
    );
  }

  return inner;
}

export function FunnelStageTabs({
  active,
  onChange,
  counts,
}: {
  active: FunnelStage | "";
  onChange: (stage: FunnelStage | "") => void;
  counts?: Partial<Record<FunnelStage, number>>;
}) {
  const stages: (FunnelStage | "")[] = ["", ...FUNNEL_STAGES];

  return (
    <div className="flex flex-wrap gap-1 border-b border-border pb-2">
      {stages.map((stage) => {
        const label = stage === "" ? "Todas" : FUNNEL_STAGE_LABELS[stage];
        const count = stage ? counts?.[stage] : undefined;
        return (
          <Button
            key={stage || "all"}
            type="button"
            size="sm"
            variant={active === stage ? "default" : "ghost"}
            className="h-8"
            onClick={() => onChange(stage)}
          >
            {label}
            {count != null ? ` (${count})` : ""}
          </Button>
        );
      })}
    </div>
  );
}
