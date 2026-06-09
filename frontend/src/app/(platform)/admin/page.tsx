"use client";

import Link from "next/link";
import { Shield, Users, Boxes, GitBranch, Building2, Plug } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { AdminNav } from "@/components/admin/admin-nav";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const SECTIONS = [
  { href: "/admin/usuarios", title: "Usuarios", desc: "Crear, editar y desactivar usuarios JAIOS", icon: Users },
  { href: "/admin/roles", title: "Roles y permisos", desc: "Matriz de roles operativos", icon: Shield },
  { href: "/admin/modulos", title: "Módulos", desc: "Activar o desactivar módulos del tenant", icon: Boxes },
  { href: "/admin/departamentos", title: "Departamentos", desc: "Estructura organizacional", icon: Building2 },
  { href: "/admin/reglas", title: "Reglas de asignación", desc: "Motor de routing operacional", icon: GitBranch },
  { href: "/admin/integraciones", title: "Integraciones", desc: "Estado y configuración general", icon: Plug },
];

export default function AdminPage() {
  return (
    <AppShell
      title="Centro de Administración"
      description="Usuarios, módulos, permisos, reglas y configuración del tenant"
    >
      <AdminNav />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {SECTIONS.map(({ href, title, desc, icon: Icon }) => (
          <Link key={href} href={href}>
            <Card className="h-full hover:border-primary/40 transition-colors">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Icon className="h-4 w-4" /> {title}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">{desc}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </AppShell>
  );
}
