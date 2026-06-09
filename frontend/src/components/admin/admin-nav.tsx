"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/admin", label: "Resumen", exact: true },
  { href: "/admin/usuarios", label: "Usuarios" },
  { href: "/admin/roles", label: "Roles" },
  { href: "/admin/modulos", label: "Módulos" },
  { href: "/admin/departamentos", label: "Departamentos" },
  { href: "/admin/reglas", label: "Reglas" },
  { href: "/admin/integraciones", label: "Integraciones" },
];

export function AdminNav() {
  const pathname = usePathname();
  return (
    <nav className="flex flex-wrap gap-2 border-b border-border pb-4 mb-6">
      {LINKS.map(({ href, label, exact }) => {
        const active = exact ? pathname === href : pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
              active ? "bg-primary/10 text-primary" : "text-muted-foreground hover:bg-muted",
            )}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
