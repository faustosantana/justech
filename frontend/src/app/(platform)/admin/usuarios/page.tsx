"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/layout/app-shell";
import { AdminNav } from "@/components/admin/admin-nav";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import { ROLE_LABELS, type AdminUser } from "@/lib/admin";

const ROLES = Object.keys(ROLE_LABELS).filter((k) => k !== "member");
const ROLES_CAN_SELECT_ALL = new Set(["owner", "admin", "gerencia"]);

type CompanyEditState = {
  userId: string;
  userName: string;
  availableCompanies: { id: number; name: string; selected: boolean }[];
  visibleCompanyIds: number[];
  defaultCompanyId: number | null;
  canSelectAll: boolean;
  userRole: string;
  saveMessage: string | null;
  saveError: string | null;
};

export default function AdminUsuariosPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [canMutate, setCanMutate] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    email: "",
    full_name: "",
    password: "JaiosTeam2026!",
    role: "usuario",
    department: "",
  });
  const [companyEdit, setCompanyEdit] = useState<CompanyEditState | null>(null);
  const [savingCompanies, setSavingCompanies] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [access, res] = await Promise.all([
        apiClient.getAdminAccess(),
        apiClient.getAdminUsers(),
      ]);
      setCanMutate(access.can_mutate);
      setUsers(res.items);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreate = async () => {
    await apiClient.createAdminUser({
      ...form,
      department: form.department || undefined,
    });
    setShowForm(false);
    load();
  };

  const handleDisable = async (id: string) => {
    if (!confirm("¿Desactivar este usuario?")) return;
    await apiClient.disableAdminUser(id);
    load();
  };

  const handleRoleChange = async (id: string, role: string) => {
    await apiClient.updateAdminUser(id, { role });
    if (companyEdit?.userId === id) {
      setCompanyEdit((prev) =>
        prev
          ? {
              ...prev,
              userRole: role,
              canSelectAll: ROLES_CAN_SELECT_ALL.has(role),
            }
          : null,
      );
    }
    load();
  };

  const openCompanyEdit = async (user: AdminUser) => {
    const data = await apiClient.getAdminUserCompanies(user.id);
    setCompanyEdit({
      userId: user.id,
      userName: user.full_name,
      availableCompanies: data.available_companies ?? [],
      visibleCompanyIds: data.visible_company_ids ?? [],
      defaultCompanyId: data.default_company_id ?? null,
      canSelectAll: data.can_select_all ?? false,
      userRole: data.user_role ?? user.role,
      saveMessage: null,
      saveError: null,
    });
  };

  const toggleCompany = (companyId: number, checked: boolean) => {
    setCompanyEdit((prev) => {
      if (!prev) return prev;
      const visibleCompanyIds = checked
        ? [...new Set([...prev.visibleCompanyIds, companyId])]
        : prev.visibleCompanyIds.filter((id) => id !== companyId);
      const defaultCompanyId =
        prev.defaultCompanyId && visibleCompanyIds.includes(prev.defaultCompanyId)
          ? prev.defaultCompanyId
          : visibleCompanyIds[0] ?? null;
      return {
        ...prev,
        visibleCompanyIds,
        defaultCompanyId,
        availableCompanies: prev.availableCompanies.map((c) =>
          c.id === companyId ? { ...c, selected: checked } : c,
        ),
        saveMessage: null,
        saveError: null,
      };
    });
  };

  const saveCompanyEdit = async () => {
    if (!companyEdit) return;
    setSavingCompanies(true);
    setCompanyEdit((prev) => (prev ? { ...prev, saveMessage: null, saveError: null } : prev));
    try {
      await apiClient.setAdminUserCompanies(companyEdit.userId, {
        visible_company_ids: companyEdit.visibleCompanyIds,
        default_company_id: companyEdit.defaultCompanyId ?? undefined,
        can_select_all: companyEdit.canSelectAll,
      });
      const refreshed = await apiClient.getAdminUserCompanies(companyEdit.userId);
      setCompanyEdit({
        userId: companyEdit.userId,
        userName: companyEdit.userName,
        availableCompanies: refreshed.available_companies ?? [],
        visibleCompanyIds: refreshed.visible_company_ids ?? [],
        defaultCompanyId: refreshed.default_company_id ?? null,
        canSelectAll: refreshed.can_select_all ?? false,
        userRole: refreshed.user_role ?? companyEdit.userRole,
        saveMessage: "Permisos guardados y confirmados tras recarga.",
        saveError: null,
      });
      load();
    } catch (err) {
      setCompanyEdit((prev) =>
        prev
          ? {
              ...prev,
              saveError: err instanceof Error ? err.message : "Error al guardar permisos",
            }
          : null,
      );
    } finally {
      setSavingCompanies(false);
    }
  };

  return (
    <AppShell title="Usuarios" description="Gestión de usuarios JAIOS del tenant">
      <AdminNav />
      <div className="space-y-4">
        {canMutate && (
          <Button size="sm" onClick={() => setShowForm(!showForm)}>
            {showForm ? "Cancelar" : "Crear usuario"}
          </Button>
        )}
        {showForm && canMutate && (
          <Card>
            <CardHeader><CardTitle className="text-base">Nuevo usuario</CardTitle></CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2">
              <input className="rounded-lg border px-3 py-2 text-sm" placeholder="Correo" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
              <input className="rounded-lg border px-3 py-2 text-sm" placeholder="Nombre completo" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
              <input className="rounded-lg border px-3 py-2 text-sm" placeholder="Contraseña" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
              <select className="rounded-lg border px-3 py-2 text-sm" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
              </select>
              <input className="rounded-lg border px-3 py-2 text-sm" placeholder="Departamento" value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} />
              <Button onClick={handleCreate}>Guardar</Button>
            </CardContent>
          </Card>
        )}
        <Card>
          <CardContent className="pt-6">
            {loading ? (
              <p className="text-sm text-muted-foreground">Cargando…</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-muted-foreground border-b">
                    <th className="pb-2">Nombre</th>
                    <th className="pb-2">Correo</th>
                    <th className="pb-2">Rol</th>
                    <th className="pb-2">Departamento</th>
                    <th className="pb-2">M365</th>
                    <th className="pb-2">Estado</th>
                    {canMutate && <th className="pb-2">Acciones</th>}
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-b border-border/50">
                      <td className="py-2 font-medium">{u.full_name}</td>
                      <td className="py-2 text-muted-foreground">{u.email}</td>
                      <td className="py-2">
                        {canMutate ? (
                          <select className="rounded border px-2 py-1 text-xs" value={u.role} onChange={(e) => handleRoleChange(u.id, e.target.value)}>
                            {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
                          </select>
                        ) : (
                          ROLE_LABELS[u.role] ?? u.role
                        )}
                      </td>
                      <td className="py-2">{u.department ?? "—"}</td>
                      <td className="py-2 text-xs">{u.m365_prepared ? u.m365_connection_status : "—"}</td>
                      <td className="py-2">{u.is_active ? "Activo" : "Inactivo"}</td>
                      {canMutate && u.is_active && (
                        <td className="py-2 space-x-2">
                          <Button
                            size="sm"
                            variant="outline"
                            data-testid={`admin-companies-btn-${u.id}`}
                            onClick={() => openCompanyEdit(u)}
                          >
                            Empresas
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => handleDisable(u.id)}>Desactivar</Button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>
        {companyEdit && canMutate && (
          <Card data-testid="admin-companies-panel">
            <CardHeader>
              <CardTitle className="text-base">
                Empresas visibles — {companyEdit.userName}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Rol</p>
                  <p className="text-sm mt-1">{ROLE_LABELS[companyEdit.userRole] ?? companyEdit.userRole}</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Puede ver todas</p>
                  <label className="mt-2 flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={companyEdit.canSelectAll}
                      disabled={!ROLES_CAN_SELECT_ALL.has(companyEdit.userRole)}
                      onChange={(e) =>
                        setCompanyEdit((prev) =>
                          prev ? { ...prev, canSelectAll: e.target.checked, saveMessage: null } : prev,
                        )
                      }
                    />
                    {ROLES_CAN_SELECT_ALL.has(companyEdit.userRole)
                      ? "Permitir selector «Todas las empresas»"
                      : "Solo roles owner/admin/gerencia pueden ver todas"}
                  </label>
                </div>
              </div>

              {companyEdit.availableCompanies.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No hay empresas Odoo disponibles. Verifique la conexión Odoo del tenant.
                </p>
              ) : (
                <div className="rounded-lg border divide-y" data-testid="admin-companies-list">
                  {companyEdit.availableCompanies.map((company) => {
                    const checked = companyEdit.visibleCompanyIds.includes(company.id);
                    return (
                      <label
                        key={company.id}
                        data-testid={`admin-company-row-${company.id}`}
                        className="flex flex-wrap items-center gap-3 px-3 py-2 text-sm hover:bg-muted/30 cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          data-testid={`admin-company-check-${company.id}`}
                          checked={checked}
                          onChange={(e) => toggleCompany(company.id, e.target.checked)}
                        />
                        <span className="font-medium flex-1">{company.name}</span>
                        <span className="text-xs text-muted-foreground">ID Odoo {company.id}</span>
                        <label className="flex items-center gap-1 text-xs text-muted-foreground">
                          <input
                            type="radio"
                            name="default-company"
                            data-testid={`admin-company-default-${company.id}`}
                            checked={companyEdit.defaultCompanyId === company.id}
                            disabled={!checked}
                            onChange={() =>
                              setCompanyEdit((prev) =>
                                prev ? { ...prev, defaultCompanyId: company.id, saveMessage: null } : prev,
                              )
                            }
                          />
                          Por defecto
                        </label>
                      </label>
                    );
                  })}
                </div>
              )}

              <div className="rounded-lg border border-dashed px-3 py-2 text-sm text-muted-foreground">
                Módulos del tenant:{" "}
                <Link href="/admin/modulos" className="text-primary hover:underline">
                  configurar en Admin → Módulos
                </Link>
                . Los permisos por usuario se heredan del rol y del tenant.
              </div>

              {companyEdit.saveMessage && (
                <div
                  data-testid="admin-companies-save-success"
                  className="rounded-lg border border-success/30 bg-success/10 px-3 py-2 text-sm text-success "
                >
                  {companyEdit.saveMessage}
                </div>
              )}
              {companyEdit.saveError && (
                <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {companyEdit.saveError}
                </div>
              )}

              <div className="flex gap-2">
                <Button size="sm" data-testid="admin-companies-save" onClick={saveCompanyEdit} disabled={savingCompanies}>
                  {savingCompanies ? "Guardando…" : "Guardar"}
                </Button>
                <Button size="sm" variant="outline" onClick={() => setCompanyEdit(null)}>Cancelar</Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </AppShell>
  );
}
