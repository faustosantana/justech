"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  AlertTriangle,
  Building2,
  FileText,
  FolderOpen,
  LineChart,
  Scale,
  Send,
  Shield,
  Target,
} from "lucide-react";

import { DOCUMENTOS_SUBMODULES } from "@/lib/documents-hub";
import { cn } from "@/lib/utils";

const ICONS: Record<string, typeof FolderOpen> = {
  folder: FolderOpen,
  building: Building2,
  scale: Scale,
  file: FileText,
  shield: Shield,
  chart: LineChart,
  alert: AlertTriangle,
  target: Target,
  outbox: Send,
};

export function DocumentsHubNav() {
  const pathname = usePathname();

  return (
    <nav className="flex flex-wrap gap-2 border-b border-border/60 pb-4">
      <Link
        href="/documentos"
        className={cn(
          "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
          pathname === "/documentos"
            ? "bg-primary text-primary-foreground"
            : "bg-muted/60 text-muted-foreground hover:bg-muted",
        )}
      >
        Dashboard
      </Link>
      {DOCUMENTOS_SUBMODULES.map(({ key, href, label }) => {
        const Icon = ICONS[key] || FileText;
        const active = pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
              active
                ? "bg-primary/10 text-primary ring-1 ring-primary/30"
                : "bg-muted/40 text-muted-foreground hover:bg-muted",
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
