"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Bot, Briefcase, FileText, Search, Sparkles, Target, TrendingUp } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api";
import type { M365MailIntelligence } from "@/lib/m365-intelligence";
import { cn } from "@/lib/utils";

function Badge({ children, variant = "default" }: { children: React.ReactNode; variant?: "default" | "warn" | "success" }) {
  return (
    <span
      className={cn(
        "inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium",
        variant === "warn" && "bg-amber-500/15 text-amber-800 dark:text-amber-200",
        variant === "success" && "bg-emerald-500/15 text-emerald-800 dark:text-emerald-200",
        variant === "default" && "bg-primary/10 text-primary",
      )}
    >
      {children}
    </span>
  );
}

export function M365MailAiPanel({
  messageId,
  accountId,
  onAction,
}: {
  messageId: string | null;
  accountId?: string | null;
  onAction?: (actionId: string) => void;
}) {
  const [data, setData] = useState<M365MailIntelligence | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!messageId) {
      setData(null);
      return;
    }
    setLoading(true);
    apiClient
      .getM365MailIntelligence(messageId, accountId ?? undefined)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [messageId, accountId]);

  if (!messageId) return null;
  if (loading) {
    return (
      <div className="border-t bg-muted/20 p-4">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Sparkles className="h-4 w-4 animate-pulse" />
          Analizando correo con JAIOS…
        </div>
      </div>
    );
  }
  if (!data) return null;

  return (
    <div className="border-t bg-gradient-to-b from-primary/5 to-transparent p-4">
      <div className="mb-3 flex items-center gap-2">
        <Bot className="h-5 w-5 text-primary" />
        <p className="font-semibold text-sm">Inteligencia JAIOS</p>
        <Badge>{data.classification_label}</Badge>
        <Badge variant={data.priority_score >= 75 ? "warn" : "default"}>{data.priority_label}</Badge>
      </div>
      <p className="mb-3 text-sm text-muted-foreground">{data.summary}</p>
      <div className="mb-3 flex flex-wrap gap-2 text-xs">
        {data.vendor && <Badge variant="success">Proveedor: {data.vendor}</Badge>}
        {data.client && <Badge>Cliente: {data.client}</Badge>}
        {data.dgcp_process_code && <Badge variant="warn">DGCP: {data.dgcp_process_code}</Badge>}
        {data.amount != null && (
          <Badge>
            {data.currency ?? "USD"} {data.amount.toLocaleString()}
          </Badge>
        )}
        <Badge>{data.sentiment === "positive" ? "Positivo" : data.sentiment === "negative" ? "Negativo" : "Neutral"}</Badge>
      </div>
      {data.products.length > 0 && (
        <p className="mb-2 text-xs text-muted-foreground">Productos: {data.products.join(", ")}</p>
      )}
      {data.risks.length > 0 && (
        <div className="mb-2 flex items-start gap-2 text-xs text-amber-700 dark:text-amber-300">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          Riesgos: {data.risks.join(", ")}
        </div>
      )}
      {data.opportunities.length > 0 && (
        <div className="mb-3 flex items-start gap-2 text-xs text-emerald-700 dark:text-emerald-300">
          <TrendingUp className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          Oportunidades: {data.opportunities.join(", ")}
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        {data.suggested_actions.map((a) =>
          a.href ? (
            <Button key={a.id} size="sm" variant="outline" asChild>
              <Link href={a.href}>
                {a.action_type === "dgcp" && <Target className="mr-1 h-3.5 w-3.5" />}
                {a.action_type === "odoo" && <Briefcase className="mr-1 h-3.5 w-3.5" />}
                {a.action_type === "prices" && <FileText className="mr-1 h-3.5 w-3.5" />}
                {a.action_type === "search" && <Search className="mr-1 h-3.5 w-3.5" />}
                {a.label}
              </Link>
            </Button>
          ) : (
            <Button key={a.id} size="sm" variant="secondary" onClick={() => onAction?.(a.id)}>
              <Sparkles className="mr-1 h-3.5 w-3.5" />
              {a.label}
            </Button>
          ),
        )}
      </div>
    </div>
  );
}
