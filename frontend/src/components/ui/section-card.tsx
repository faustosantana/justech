import Link from "next/link";

import { ArrowRight } from "lucide-react";

import { cn } from "@/lib/utils";

interface SectionCardProps {
  title: string;
  description?: string;
  href?: string;
  actionLabel?: string;
  className?: string;
  children: React.ReactNode;
}

export function SectionCard({
  title,
  description,
  href,
  actionLabel = "Abrir",
  className,
  children,
}: SectionCardProps) {
  return (
    <section className={cn("brand-surface-accent overflow-hidden", className)}>
      <div className="brand-panel-header flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold">{title}</h2>
          {description && <p className="mt-1 text-sm text-muted-foreground">{description}</p>}
        </div>
        {href && (
          <Link href={href} className="inline-flex items-center gap-1 text-sm font-medium text-primary">
            {actionLabel}
            <ArrowRight className="h-4 w-4" />
          </Link>
        )}
      </div>
      <div className="p-5">{children}</div>
    </section>
  );
}
