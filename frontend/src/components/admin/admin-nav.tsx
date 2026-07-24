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

/** Navegación horizontal del centro /admin (requerida por páginas legacy). */
export function AdminNav() {
  const pathname = usePathname();
  return (
    <nav className="mb-4 flex flex-wrap gap-2 border-b border-border pb-3">
      {LINKS.map((item) => {
        const active = item.exact
          ? pathname === item.href
          : pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "rounded-md px-3 py-1.5 text-sm",
              active
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
