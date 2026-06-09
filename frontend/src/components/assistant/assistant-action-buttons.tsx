"use client";

import Link from "next/link";
import { ExternalLink, Eye } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { AssistantAction } from "@/lib/assistant-types";

interface AssistantActionButtonsProps {
  actions: AssistantAction[];
  compact?: boolean;
  onQuickView?: (entityType: string, entityId: string, label?: string) => void;
  onNavigate?: () => void;
}

export function AssistantActionButtons({
  actions,
  compact = false,
  onQuickView,
  onNavigate,
}: AssistantActionButtonsProps) {
  if (!actions.length) return null;

  return (
    <div className={`flex flex-wrap gap-1 ${compact ? "" : "mt-1"}`}>
      {actions.map((action, i) => {
        if (action.type === "internal_link" && action.url) {
          return (
            <Button key={i} variant="outline" size="sm" className="h-7 text-[10px] px-2" asChild>
              <Link href={action.url} onClick={onNavigate}>
                {action.label}
              </Link>
            </Button>
          );
        }
        if (action.type === "external_link" && action.url) {
          return (
            <Button key={i} variant="outline" size="sm" className="h-7 text-[10px] px-2" asChild>
              <a href={action.url} target="_blank" rel="noopener noreferrer">
                {action.label}
                <ExternalLink className="ml-1 h-3 w-3" />
              </a>
            </Button>
          );
        }
        if (action.type === "quick_view" && action.entity_type && action.entity_id) {
          return (
            <Button
              key={i}
              variant="secondary"
              size="sm"
              className="h-7 text-[10px] px-2"
              onClick={() => onQuickView?.(action.entity_type!, action.entity_id!, action.label)}
            >
              <Eye className="mr-1 h-3 w-3" />
              {action.label}
            </Button>
          );
        }
        return null;
      })}
    </div>
  );
}
