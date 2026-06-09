import Link from "next/link";

import { cn } from "@/lib/utils";

interface AlertCardProps {
  title: string;
  source: string;
  priority: "danger" | "warning" | "primary";
  href: string;
  assignee?: string;
}

const priorityClasses = {
  danger: "border-destructive/30 bg-destructive/5",
  warning: "border-warning/40 bg-warning/5",
  primary: "border-primary/20 bg-primary/5",
};

export function AlertCard({ title, source, priority, href, assignee }: AlertCardProps) {
  return (
    <Link
      href={href}
      className={cn(
        "block rounded-xl border p-4 transition hover:shadow-sm",
        priorityClasses[priority],
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium">{title}</p>
          <p className="mt-1 text-xs text-muted-foreground">Fuente: {source}</p>
          {assignee && <p className="mt-1 text-xs text-muted-foreground">Responsable sugerido: {assignee}</p>}
        </div>
        <span className="shrink-0 text-xs font-medium text-primary">Revisar →</span>
      </div>
    </Link>
  );
}
