"use client";

import { useCallback, useEffect, useState } from "react";
import { Search } from "lucide-react";

import { apiClient } from "@/lib/api";
import { cn } from "@/lib/utils";

export interface TenantUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
}

interface UserSelectorProps {
  value: string | null;
  onChange: (userId: string | null, user: TenantUser | null) => void;
  label: string;
  placeholder?: string;
  allowEmpty?: boolean;
  emptyLabel?: string;
  className?: string;
}

const ROLE_LABELS: Record<string, string> = {
  owner: "Propietario",
  admin: "Administrador",
  member: "Miembro",
};

export function UserSelector({
  value,
  onChange,
  label,
  placeholder = "Buscar por nombre o correo…",
  allowEmpty = true,
  emptyLabel = "Sin asignar",
  className,
}: UserSelectorProps) {
  const [users, setUsers] = useState<TenantUser[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);

  const load = useCallback(async (q: string) => {
    setLoading(true);
    try {
      const res = await apiClient.getTenantUsers({ search: q || undefined, limit: 50 });
      setUsers(res.items);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load("");
  }, [load]);

  useEffect(() => {
    const t = setTimeout(() => load(search), 250);
    return () => clearTimeout(t);
  }, [search, load]);

  const selected = users.find((u) => u.id === value);

  return (
    <div className={cn("space-y-1.5", className)}>
      <label className="text-sm font-medium text-foreground">{label}</label>
      <div className="relative">
        <button
          type="button"
          className="w-full rounded-lg border border-border bg-background px-3 py-2 text-left text-sm"
          onClick={() => setOpen(!open)}
        >
          {selected ? (
            <span>
              {selected.full_name} · {selected.email}
              <span className="text-muted-foreground ml-1">
                ({ROLE_LABELS[selected.role] ?? selected.role})
              </span>
            </span>
          ) : (
            <span className="text-muted-foreground">{emptyLabel}</span>
          )}
        </button>
        {open && (
          <div className="absolute z-20 mt-1 w-full rounded-lg border border-border bg-card shadow-lg">
            <div className="relative p-2 border-b border-border">
              <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <input
                className="w-full rounded-md border border-border bg-background py-1.5 pl-9 pr-3 text-sm"
                placeholder={placeholder}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                autoFocus
              />
            </div>
            <ul className="max-h-48 overflow-y-auto p-1">
              {allowEmpty && (
                <li>
                  <button
                    type="button"
                    className="w-full rounded-md px-3 py-2 text-left text-sm hover:bg-muted"
                    onClick={() => {
                      onChange(null, null);
                      setOpen(false);
                    }}
                  >
                    {emptyLabel}
                  </button>
                </li>
              )}
              {loading ? (
                <li className="px-3 py-2 text-sm text-muted-foreground">Cargando…</li>
              ) : users.length === 0 ? (
                <li className="px-3 py-2 text-sm text-muted-foreground">Sin usuarios</li>
              ) : (
                users.map((u) => (
                  <li key={u.id}>
                    <button
                      type="button"
                      className={cn(
                        "w-full rounded-md px-3 py-2 text-left text-sm hover:bg-muted",
                        value === u.id && "bg-primary/10 text-primary",
                      )}
                      onClick={() => {
                        onChange(u.id, u);
                        setOpen(false);
                      }}
                    >
                      <span className="font-medium">{u.full_name}</span>
                      <span className="block text-xs text-muted-foreground">
                        {u.email} · {ROLE_LABELS[u.role] ?? u.role}
                      </span>
                    </button>
                  </li>
                ))
              )}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
