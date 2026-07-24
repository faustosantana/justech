"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { AppShell } from "@/components/layout/app-shell";
import { BulkActionsBar } from "@/components/ui/bulk-actions-bar";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ApiError, apiClient } from "@/lib/api";
import { getAccessToken, getUserRole } from "@/lib/auth";
import {
  canAccessLotteryAdmin,
  healthStatusLabel,
  type LotteryAdminLottery,
} from "@/lib/lottery";

type BoolField =
  | "is_visible_catalog"
  | "is_searchable"
  | "is_ai_enabled"
  | "is_sync_enabled"
  | "is_auto_write_enabled"
  | "is_featured";

const DANGEROUS_ENABLES: Partial<Record<BoolField, string>> = {
  is_sync_enabled: "¿Activar sincronización? Esto puede escribir datos en la base.",
  is_auto_write_enabled: "¿Activar auto-escritura? Operación de alto riesgo en producción.",
};

function FlagToggle({
  checked,
  label,
  disabled,
  onChange,
}: {
  checked: boolean;
  label: string;
  disabled?: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <label className="inline-flex items-center gap-1 text-xs" title={label}>
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        aria-label={label}
      />
      <span className="sr-only">{label}</span>
    </label>
  );
}

export default function LotteryAdminLotteriesPage() {
  const router = useRouter();
  const [rows, setRows] = useState<LotteryAdminLottery[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [q, setQ] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [permissions, setPermissions] = useState<string[]>([]);

  const role = typeof window !== "undefined" ? getUserRole() : null;
  const allowed = canAccessLotteryAdmin(role, permissions);

  const load = useCallback(async () => {
    if (!getAccessToken()) {
      router.replace("/login?session=expired");
      return;
    }
    try {
      const access = await apiClient.getPlatformAccess().catch(() => null);
      const perms = access?.permissions ?? [];
      setPermissions(perms);
      if (!canAccessLotteryAdmin(getUserRole(), perms)) {
        setError("Acceso denegado — se requiere rol admin u permiso lottery.admin");
        setLoading(false);
        return;
      }
      const data = await apiClient.getLotteryAdminLotteries({
        q: search || undefined,
        limit: 200,
        offset: 0,
      });
      setRows(data);
      setSelected(new Set());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar loterías admin");
    } finally {
      setLoading(false);
    }
  }, [router, search]);

  useEffect(() => {
    void load();
  }, [load]);

  const allIds = useMemo(() => rows.map((r) => r.id), [rows]);

  const patchField = async (row: LotteryAdminLottery, field: BoolField, value: boolean) => {
    if (value && DANGEROUS_ENABLES[field]) {
      const ok = window.confirm(DANGEROUS_ENABLES[field]);
      if (!ok) return;
    }
    setBusyId(row.id);
    setMsg(null);
    try {
      const updated = await apiClient.patchLotteryAdminLottery(row.id, { [field]: value });
      setRows((prev) => prev.map((r) => (r.id === row.id ? updated : r)));
      setMsg(`${row.name}: actualizado`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al actualizar");
    } finally {
      setBusyId(null);
    }
  };

  const patchOrder = async (row: LotteryAdminLottery, display_order: number) => {
    if (!Number.isFinite(display_order) || display_order < 0) return;
    setBusyId(row.id);
    try {
      const updated = await apiClient.patchLotteryAdminLottery(row.id, { display_order });
      setRows((prev) => prev.map((r) => (r.id === row.id ? updated : r)));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al actualizar orden");
    } finally {
      setBusyId(null);
    }
  };

  const runBulk = async (action: string, confirmMsg?: string) => {
    const ids = [...selected];
    if (!ids.length) return;
    if (confirmMsg && !window.confirm(confirmMsg)) return;
    const res = await apiClient.postLotteryAdminLotteriesBulk({ lottery_ids: ids, action });
    setMsg(`${res.updated} lotería(s) — acción: ${res.action}`);
    await load();
  };

  if (!allowed && !loading && error) {
    return (
      <AppShell title="Admin loterías" description="Control de visibilidad y sync">
        <Card className="border-destructive/40">
          <CardContent className="py-6 text-sm text-destructive">{error}</CardContent>
        </Card>
      </AppShell>
    );
  }

  return (
    <AppShell title="Admin loterías" description="Centro de operaciones Lottery 3.0 — visibilidad, sync, ventanas">
      <div className="mb-4">
        <Button asChild variant="outline" size="sm">
          <Link href="/lottery/admin/lotteries/archivo-historico">Archivo histórico (fuera del universo activo)</Link>
        </Button>
      </div>
      <div className="mb-3 flex flex-wrap gap-2 text-sm">
        <Link href="/lottery" className="text-primary underline">
          Inicio
        </Link>
        <Link href="/lottery/admin/sync" className="text-primary underline">
          Admin sync
        </Link>
        <Link href="/lottery/admin/scheduler" className="text-primary underline">
          Scheduler
        </Link>
        <Link href="/lottery/admin/ai" className="text-primary underline">
          Centro de IA
        </Link>
      </div>

      <form
        className="mb-3 flex flex-wrap gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          setSearch(q.trim());
        }}
      >
        <Input
          aria-label="Filtrar loterías"
          placeholder="Buscar por nombre…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="max-w-xs"
        />
        <Button type="submit" variant="outline" size="sm">
          Filtrar
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={() => void load()} disabled={loading}>
          Actualizar
        </Button>
      </form>

      {loading && <p className="text-sm text-muted-foreground" role="status">Cargando…</p>}
      {error && <p className="mb-2 text-sm text-destructive">{error}</p>}
      {msg && <p className="mb-2 text-sm text-muted-foreground">{msg}</p>}

      <BulkActionsBar
        selectedIds={[...selected]}
        allIds={allIds}
        onSelectAll={() => setSelected(new Set(allIds))}
        onClearSelection={() => setSelected(new Set())}
        actions={[
          {
            id: "show",
            label: "Mostrar catálogo",
            onRun: () => runBulk("show"),
          },
          {
            id: "hide",
            label: "Ocultar catálogo",
            onRun: (ids) => runBulk("hide"),
          },
          {
            id: "allow_search",
            label: "Permitir búsqueda",
            onRun: () => runBulk("allow_search"),
          },
          {
            id: "block_search",
            label: "Bloquear búsqueda",
            onRun: () => runBulk("block_search"),
          },
          {
            id: "enable_ai",
            label: "Activar IA",
            onRun: () => runBulk("enable_ai"),
          },
          {
            id: "disable_ai",
            label: "Desactivar IA",
            onRun: () => runBulk("disable_ai"),
          },
          {
            id: "enable_sync",
            label: "Activar sync",
            onRun: () =>
              runBulk("enable_sync", "¿Activar sync en las loterías seleccionadas?"),
          },
          {
            id: "disable_sync",
            label: "Desactivar sync",
            onRun: () => runBulk("disable_sync"),
          },
        ]}
      />

      {!loading && rows.length === 0 && (
        <Card>
          <CardContent className="py-8 text-center text-sm text-muted-foreground">
            No hay loterías que mostrar.
          </CardContent>
        </Card>
      )}

      {rows.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-border/80">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-8" />
                <TableHead>Nombre</TableHead>
                <TableHead>Visible</TableHead>
                <TableHead>Búsqueda</TableHead>
                <TableHead>IA</TableHead>
                <TableHead>Sync</TableHead>
                <TableHead>Auto write</TableHead>
                <TableHead>Destacada</TableHead>
                <TableHead>Orden</TableHead>
                <TableHead>Estado</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.id} className={busyId === row.id ? "opacity-60" : undefined}>
                  <TableCell>
                    <input
                      type="checkbox"
                      checked={selected.has(row.id)}
                      onChange={(e) => {
                        setSelected((prev) => {
                          const next = new Set(prev);
                          if (e.target.checked) next.add(row.id);
                          else next.delete(row.id);
                          return next;
                        });
                      }}
                      aria-label={`Seleccionar ${row.name}`}
                    />
                  </TableCell>
                  <TableCell>
                    <div>
                      <p className="font-medium">{row.name}</p>
                      <p className="text-xs text-muted-foreground">{row.slug}</p>
                    </div>
                  </TableCell>
                  <TableCell>
                    <FlagToggle
                      checked={row.is_visible_catalog}
                      label="Visible en catálogo"
                      disabled={busyId === row.id}
                      onChange={(v) => void patchField(row, "is_visible_catalog", v)}
                    />
                  </TableCell>
                  <TableCell>
                    <FlagToggle
                      checked={row.is_searchable}
                      label="Buscable"
                      disabled={busyId === row.id}
                      onChange={(v) => void patchField(row, "is_searchable", v)}
                    />
                  </TableCell>
                  <TableCell>
                    <FlagToggle
                      checked={row.is_ai_enabled}
                      label="IA habilitada"
                      disabled={busyId === row.id}
                      onChange={(v) => void patchField(row, "is_ai_enabled", v)}
                    />
                  </TableCell>
                  <TableCell>
                    <FlagToggle
                      checked={row.is_sync_enabled}
                      label="Sync habilitado"
                      disabled={busyId === row.id}
                      onChange={(v) => void patchField(row, "is_sync_enabled", v)}
                    />
                  </TableCell>
                  <TableCell>
                    <FlagToggle
                      checked={row.is_auto_write_enabled}
                      label="Auto-escritura"
                      disabled={busyId === row.id}
                      onChange={(v) => void patchField(row, "is_auto_write_enabled", v)}
                    />
                  </TableCell>
                  <TableCell>
                    <FlagToggle
                      checked={row.is_featured}
                      label="Destacada"
                      disabled={busyId === row.id}
                      onChange={(v) => void patchField(row, "is_featured", v)}
                    />
                  </TableCell>
                  <TableCell>
                    <Input
                      type="number"
                      className="h-8 w-20"
                      defaultValue={row.display_order}
                      min={0}
                      aria-label={`Orden ${row.name}`}
                      onBlur={(e) => {
                        const n = Number(e.target.value);
                        if (n !== row.display_order) void patchOrder(row, n);
                      }}
                    />
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        row.health_status === "healthy"
                          ? "success"
                          : row.health_status === "error"
                            ? "danger"
                            : "muted"
                      }
                    >
                      {healthStatusLabel(row.health_status)}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </AppShell>
  );
}
