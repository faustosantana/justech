"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Building2,
  FolderOpen,
  Home,
  Key,
  Plug,
  Palette,
  ScrollText,
  Shield,
  Users,
} from "lucide-react";

import { cn } from "@/lib/utils";

export const ADMIN_NAV = [
  { href: "/configuracion", label: "General", icon: Home, exact: true },
  { href: "/configuracion/apariencia", label: "Apariencia", icon: Palette },
  { href: "/configuracion/empresas", label: "Empresa activa (tenant)", icon: Building2 },
  { href: "/configuracion/usuarios", label: "Usuarios", icon: Users },
  { href: "/configuracion/roles", label: "Roles y permisos", icon: Shield },
  { href: "/configuracion/modulos", label: "Módulos", icon: Plug },
  { href: "/configuracion/reglas", label: "Reglas de asignación", icon: ScrollText },
  { href: "/configuracion/departamentos", label: "Departamentos", icon: Building2 },
  { href: "/configuracion/integraciones", label: "Integraciones", icon: Plug },
  { href: "/configuracion/integraciones/proveedores", label: "Integraciones de Proveedores", icon: Plug },
  { href: "/configuracion/apis", label: "APIs / Conectores", icon: Key },
  { href: "/configuracion/repositorios", label: "Repositorios", icon: FolderOpen },
  { href: "/configuracion/seguridad", label: "Seguridad", icon: Shield },
  { href: "/configuracion/auditoria", label: "Logs / Auditoría", icon: ScrollText },
  { href: "/configuracion/estado", label: "Estado del sistema", icon: Activity },
];

type AdminNavItem = (typeof ADMIN_NAV)[number] & { exact?: boolean };

export function AdminSidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-full shrink-0 flex-col rounded-xl border border-border bg-card shadow-sm lg:w-60 xl:w-64">
      <div className="border-b border-border px-4 py-4">
        <p className="text-xs font-semibold uppercase tracking-wider text-primary">Panel Administrativo</p>
        <p className="mt-0.5 text-xs text-muted-foreground">Configuración de JAIOS</p>
      </div>
      <nav className="flex flex-col gap-0.5 p-2">
        {ADMIN_NAV.map((item: AdminNavItem) => {
          const active = item.exact
            ? pathname === item.href
            : pathname === item.href || pathname.startsWith(`${item.href}/`);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors",
                active
                  ? "bg-primary/10 font-medium text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto border-t border-border p-3">
        <Link
          href="/dashboard"
          className="flex items-center justify-center rounded-lg border border-border px-3 py-2 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          ← Volver a la aplicación
        </Link>
      </div>
    </aside>
  );
}
