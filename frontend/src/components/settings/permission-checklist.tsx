"use client";

import { CheckCircle2, XCircle } from "lucide-react";

import { cn } from "@/lib/utils";

type PermissionItem = {
  key: string;
  label: string;
  granted: boolean;
  detail?: string;
};

export function PermissionChecklist({ items, title = "Permisos" }: { items: PermissionItem[]; title?: string }) {
  if (!items.length) return null;

  return (
    <div className="space-y-2">
      <p className="text-sm font-medium">{title}</p>
      <ul className="space-y-1.5">
        {items.map((item) => (
          <li key={item.key} className="flex items-start gap-2 text-sm">
            {item.granted ? (
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" />
            ) : (
              <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
            )}
            <span className={cn(!item.granted && "text-muted-foreground")}>
              {item.label}
              {item.detail ? <span className="block text-xs text-muted-foreground">{item.detail}</span> : null}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
