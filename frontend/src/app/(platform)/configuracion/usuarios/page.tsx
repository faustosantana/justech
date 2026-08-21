"use client";

import Link from "next/link";
import { MoreHorizontal } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AdminPageHeader } from "@/components/admin/admin-page-header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient, ApiError } from "@/lib/api";
import { ROLE_LABELS, adminUserRoles, type AdminUser } from "@/lib/admin";
import { cn } from "@/lib/utils";

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
  userRoles: string[];
  saveMessage: string | null;
  saveError: string | null;
};

type Flash = { type: "ok" | "err"; text: string } | null;

export default function AdminUsuariosPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [canMutate, setCanMutate] = useState(false);
  const [loading, setLoading] = useState(true);
  const [flash, setFlash] = useState<Flash>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    email: "",
    full_name: "",
    password: "",
    roles: ["usuario"] as string[],
    department: "",
  });
  const [companyEdit, setCompanyEdit] = useState<CompanyEditState | null>(null);
  const [savingCompanies, setSavingCompanies] = useState(false);
  const [menuUserId, setMenuUserId] = useState<string | null>(null);
  const [rolesEdit, setRolesEdit] = useState<{ user: AdminUser; selected: string[] } | null>(null);
  const [passwordEdit, setPasswordEdit] = useState<{
    user: AdminUser;
    password: string;
    confirm: string;
    show: boolean;
  } | null>(null);
  const [busy, setBusy] = useState(false);

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
    void load();
  }, [load]);

  const showOk = (text: string) => setFlash({ type: "ok", text });
  const showErr = (err: unknown, fallback: string) => {
    const msg =
      err instanceof ApiError
        ? String((err.data as { detail?: string })?.detail ?? err.message)
        : err instanceof Error
          ? err.message
          : fallback;
    setFlash({ type: "err", text: msg || fallback });
  };

  const handleCreate = async () => {
    setBusy(true);
    try {
      await apiClient.createAdminUser({
        email: form.email,
        full_name: form.full_name,
        password: form.password,
        roles: form.roles,
        department: form.department || undefined,
      });
      setShowForm(false);
      setForm({ email: "", full_name: "", password: "", roles: ["usuario"], department: "" });
      showOk("Usuario creado correctamente.");
      await load();
    } catch (e) {
      showErr(e, "No se pudo crear el usuario.");
    } finally {
      setBusy(false);
    }
  };

  const handleStatus = async (user: AdminUser, activate: boolean) => {
    setMenuUserId(null);
    if (!activate) {
      const open = user.open_tasks_count ?? 0;
      const warn =
        open > 0
          ? `\n\nEste usuario tiene ${open} tarea(s) abierta(s).\nPuedes desactivarlo y mantener las asignaciones históricas, o reasignar las tareas antes.`
          : "";
      if (
        !confirm(
          `Desactivar usuario\n\n${user.full_name} ya no podrá iniciar sesión ni acceder a JAIOS.\nSus datos, tareas e histórico permanecerán intactos.${warn}\n\n¿Desactivar?`,
        )
      ) {
        return;
      }
    }
    setBusy(true);
    try {
      const res = await apiClient.setAdminUserStatus(user.id, activate);
      showOk(res.message || (activate ? "Usuario activado correctamente." : "Usuario desactivado correctamente."));
      await load();
    } catch (e) {
      showErr(e, "No se pudo actualizar el usuario.");
    } finally {
      setBusy(false);
    }
  };

  const saveRoles = async () => {
    if (!rolesEdit) return;
    if (rolesEdit.selected.length === 0) {
      showErr(new Error("Debe seleccionar al menos un rol"), "Debe seleccionar al menos un rol");
      return;
    }
    setBusy(true);
    try {
      const res = await apiClient.setAdminUserRoles(rolesEdit.user.id, rolesEdit.selected);
      showOk(res.message || "Roles actualizados.");
      setRolesEdit(null);
      await load();
    } catch (e) {
      showErr(e, "No se pudo actualizar el usuario.");
    } finally {
      setBusy(false);
    }
  };

  const savePassword = async () => {
    if (!passwordEdit) return;
    if (passwordEdit.password.length < 8) {
      showErr(new Error("Mínimo 8 caracteres"), "La contraseña debe tener al menos 8 caracteres");
      return;
    }
    if (passwordEdit.password !== passwordEdit.confirm) {
      showErr(new Error("No coinciden"), "La confirmación de contraseña no coincide");
      return;
    }
    setBusy(true);
    try {
      const res = await apiClient.resetAdminUserPassword(
        passwordEdit.user.id,
        passwordEdit.password,
        passwordEdit.confirm,
      );
      showOk(res.message || "Contraseña actualizada correctamente.");
      setPasswordEdit(null);
    } catch (e) {
      showErr(e, "No se pudo actualizar el usuario.");
    } finally {
      setBusy(false);
    }
  };

  const openCompanyEdit = async (user: AdminUser) => {
    setMenuUserId(null);
    const data = await apiClient.getAdminUserCompanies(user.id);
    const roles = adminUserRoles(user);
    setCompanyEdit({
      userId: user.id,
      userName: user.full_name,
      availableCompanies: data.available_companies ?? [],
      visibleCompanyIds: data.visible_company_ids ?? [],
      defaultCompanyId: data.default_company_id ?? null,
      canSelectAll: data.can_select_all ?? false,
      userRole: data.user_role ?? user.role,
      userRoles: roles,
      saveMessage: null,
      saveError: null,
    });
  };

  const canSelectAllRoles = useMemo(() => {
    if (!companyEdit) return false;
    return companyEdit.userRoles.some((r) => ROLES_CAN_SELECT_ALL.has(r));
  }, [companyEdit]);

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
        ...companyEdit,
        availableCompanies: refreshed.available_companies ?? [],
        visibleCompanyIds: refreshed.visible_company_ids ?? [],
        defaultCompanyId: refreshed.default_company_id ?? null,
        canSelectAll: refreshed.can_select_all ?? false,
        userRole: refreshed.user_role ?? companyEdit.userRole,
        saveMessage: "Permisos de empresas guardados.",
        saveError: null,
      });
      showOk("Empresas actualizadas.");
      await load();
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

  const toggleFormRole = (role: string) => {
    setForm((prev) => {
      const has = prev.roles.includes(role);
      const roles = has ? prev.roles.filter((r) => r !== role) : [...prev.roles, role];
      return { ...prev, roles: roles.length ? roles : ["usuario"] };
    });
  };

  return (
    <div>
      <AdminPageHeader
        title="Usuarios y roles"
        description="Activar, desactivar, multirol, contraseñas y empresas"
      />
      <div className="space-y-4">
        {flash && (
          <div
            className={cn(
              "rounded-md border px-3 py-2 text-sm",
              flash.type === "ok"
                ? "border-success/30 bg-success/10 text-success"
                : "border-destructive/40 bg-destructive/10 text-destructive",
            )}
          >
            {flash.text}
          </div>
        )}

        {canMutate && (
          <Button size="sm" onClick={() => setShowForm(!showForm)}>
            {showForm ? "Cancelar" : "Crear usuario"}
          </Button>
        )}

        {showForm && canMutate && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Nuevo usuario</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2">
              <input
                className="rounded-lg border px-3 py-2 text-sm"
                placeholder="Correo"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
              <input
                className="rounded-lg border px-3 py-2 text-sm"
                placeholder="Nombre completo"
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              />
              <input
                className="rounded-lg border px-3 py-2 text-sm"
                placeholder="Contraseña inicial (mín. 8)"
                type="password"
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
              <input
                className="rounded-lg border px-3 py-2 text-sm"
                placeholder="Departamento"
                value={form.department}
                onChange={(e) => setForm({ ...form, department: e.target.value })}
              />
              <div className="sm:col-span-2 space-y-2">
                <p className="text-xs font-medium text-muted-foreground">Roles</p>
                <div className="flex flex-wrap gap-2">
                  {ROLES.map((r) => (
                    <label key={r} className="flex items-center gap-1.5 rounded border px-2 py-1 text-xs">
                      <input
                        type="checkbox"
                        checked={form.roles.includes(r)}
                        onChange={() => toggleFormRole(r)}
                      />
                      {ROLE_LABELS[r]}
                    </label>
                  ))}
                </div>
              </div>
              <Button onClick={() => void handleCreate()} disabled={busy}>
                Guardar
              </Button>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardContent className="pt-6 overflow-x-auto">
            {loading ? (
              <p className="text-sm text-muted-foreground">Cargando…</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-muted-foreground border-b">
                    <th className="pb-2">Nombre</th>
                    <th className="pb-2">Correo</th>
                    <th className="pb-2">Roles</th>
                    <th className="pb-2">Departamento</th>
                    <th className="pb-2">M365</th>
                    <th className="pb-2">Estado</th>
                    {canMutate && <th className="pb-2">Acciones</th>}
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => {
                    const roles = adminUserRoles(u);
                    return (
                      <tr key={u.id} className="border-b border-border/50 align-top">
                        <td className="py-2 font-medium">{u.full_name}</td>
                        <td className="py-2 text-muted-foreground">{u.email}</td>
                        <td className="py-2">
                          <div className="flex flex-wrap gap-1">
                            {roles.map((r) => (
                              <span
                                key={r}
                                className="rounded-md bg-muted px-1.5 py-0.5 text-[11px] font-medium"
                              >
                                {ROLE_LABELS[r] ?? r}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td className="py-2">{u.department ?? "—"}</td>
                        <td className="py-2 text-xs">{u.m365_prepared ? u.m365_connection_status : "—"}</td>
                        <td className="py-2">
                          <span
                            className={cn(
                              "rounded-full px-2 py-0.5 text-[11px] font-medium",
                              u.is_active
                                ? "bg-emerald-500/15 text-emerald-700"
                                : "bg-muted text-muted-foreground",
                            )}
                          >
                            {u.is_active ? "Activo" : "Inactivo"}
                          </span>
                        </td>
                        {canMutate && (
                          <td className="py-2">
                            <div className="relative flex items-center gap-1">
                              <Button
                                size="sm"
                                variant="outline"
                                data-testid={`admin-companies-btn-${u.id}`}
                                onClick={() => void openCompanyEdit(u)}
                              >
                                Empresas
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                aria-label="Más acciones"
                                onClick={() =>
                                  setMenuUserId((id) => (id === u.id ? null : u.id))
                                }
                              >
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                              {menuUserId === u.id && (
                                <div className="absolute right-0 top-8 z-20 min-w-[180px] rounded-md border bg-background p-1 shadow-md">
                                  <button
                                    type="button"
                                    className="block w-full rounded px-2 py-1.5 text-left text-xs hover:bg-muted"
                                    onClick={() => {
                                      setMenuUserId(null);
                                      setRolesEdit({ user: u, selected: [...roles] });
                                    }}
                                  >
                                    Editar roles
                                  </button>
                                  <button
                                    type="button"
                                    className="block w-full rounded px-2 py-1.5 text-left text-xs hover:bg-muted"
                                    onClick={() => {
                                      setMenuUserId(null);
                                      setPasswordEdit({
                                        user: u,
                                        password: "",
                                        confirm: "",
                                        show: false,
                                      });
                                    }}
                                  >
                                    Cambiar contraseña
                                  </button>
                                  <button
                                    type="button"
                                    className="block w-full rounded px-2 py-1.5 text-left text-xs hover:bg-muted"
                                    onClick={() => void openCompanyEdit(u)}
                                  >
                                    Empresas
                                  </button>
                                  {u.is_active ? (
                                    <button
                                      type="button"
                                      className="block w-full rounded px-2 py-1.5 text-left text-xs text-destructive hover:bg-muted"
                                      onClick={() => void handleStatus(u, false)}
                                    >
                                      Desactivar
                                    </button>
                                  ) : (
                                    <button
                                      type="button"
                                      className="block w-full rounded px-2 py-1.5 text-left text-xs hover:bg-muted"
                                      onClick={() => void handleStatus(u, true)}
                                    >
                                      Activar
                                    </button>
                                  )}
                                </div>
                              )}
                            </div>
                          </td>
                        )}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </CardContent>
        </Card>

        {rolesEdit && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Roles de {rolesEdit.user.full_name}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="grid gap-2 sm:grid-cols-2">
                {ROLES.map((r) => (
                  <label key={r} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={rolesEdit.selected.includes(r)}
                      onChange={() =>
                        setRolesEdit((prev) => {
                          if (!prev) return prev;
                          const has = prev.selected.includes(r);
                          const selected = has
                            ? prev.selected.filter((x) => x !== r)
                            : [...prev.selected, r];
                          return { ...prev, selected };
                        })
                      }
                    />
                    {ROLE_LABELS[r]}
                  </label>
                ))}
              </div>
              <div className="flex gap-2">
                <Button size="sm" onClick={() => void saveRoles()} disabled={busy}>
                  Guardar
                </Button>
                <Button size="sm" variant="outline" onClick={() => setRolesEdit(null)}>
                  Cancelar
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {passwordEdit && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Cambiar contraseña</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 max-w-md">
              <p className="text-sm">
                <span className="font-medium">{passwordEdit.user.full_name}</span>
                <br />
                <span className="text-muted-foreground">{passwordEdit.user.email}</span>
              </p>
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">Nueva contraseña</label>
                <div className="flex gap-2">
                  <input
                    className="flex-1 rounded-lg border px-3 py-2 text-sm"
                    type={passwordEdit.show ? "text" : "password"}
                    value={passwordEdit.password}
                    onChange={(e) =>
                      setPasswordEdit((p) => (p ? { ...p, password: e.target.value } : p))
                    }
                  />
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() =>
                      setPasswordEdit((p) => (p ? { ...p, show: !p.show } : p))
                    }
                  >
                    {passwordEdit.show ? "Ocultar" : "Ver"}
                  </Button>
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">Confirmar contraseña</label>
                <input
                  className="w-full rounded-lg border px-3 py-2 text-sm"
                  type={passwordEdit.show ? "text" : "password"}
                  value={passwordEdit.confirm}
                  onChange={(e) =>
                    setPasswordEdit((p) => (p ? { ...p, confirm: e.target.value } : p))
                  }
                />
              </div>
              <div className="flex gap-2">
                <Button size="sm" onClick={() => void savePassword()} disabled={busy}>
                  Cambiar contraseña
                </Button>
                <Button size="sm" variant="outline" onClick={() => setPasswordEdit(null)}>
                  Cancelar
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

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
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    Roles
                  </p>
                  <p className="text-sm mt-1">
                    {companyEdit.userRoles.map((r) => ROLE_LABELS[r] ?? r).join(", ")}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    Puede ver todas
                  </p>
                  <label className="mt-2 flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={companyEdit.canSelectAll}
                      disabled={!canSelectAllRoles}
                      onChange={(e) =>
                        setCompanyEdit((prev) =>
                          prev ? { ...prev, canSelectAll: e.target.checked, saveMessage: null } : prev,
                        )
                      }
                    />
                    {canSelectAllRoles
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
                                prev
                                  ? { ...prev, defaultCompanyId: company.id, saveMessage: null }
                                  : prev,
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
                <Link href="/configuracion/modulos" className="text-primary hover:underline">
                  configurar en Admin → Módulos
                </Link>
                . Los permisos efectivos son la unión de los roles asignados.
              </div>

              {companyEdit.saveMessage && (
                <div
                  data-testid="admin-companies-save-success"
                  className="rounded-lg border border-success/30 bg-success/10 px-3 py-2 text-sm text-success"
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
                <Button
                  size="sm"
                  data-testid="admin-companies-save"
                  onClick={() => void saveCompanyEdit()}
                  disabled={savingCompanies}
                >
                  {savingCompanies ? "Guardando…" : "Guardar"}
                </Button>
                <Button size="sm" variant="outline" onClick={() => setCompanyEdit(null)}>
                  Cancelar
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
