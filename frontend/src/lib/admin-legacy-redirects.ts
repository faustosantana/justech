/** Mapa rutas legacy `/admin/*` → canónico `/configuracion/*` (PR-1.4). */
export const ADMIN_LEGACY_REDIRECTS: Record<string, string> = {
  "/admin": "/configuracion",
  "/admin/usuarios": "/configuracion/usuarios",
  "/admin/roles": "/configuracion/roles",
  "/admin/modulos": "/configuracion/modulos",
  "/admin/departamentos": "/configuracion/departamentos",
  "/admin/reglas": "/configuracion/reglas",
  "/admin/integraciones": "/configuracion/integraciones",
  "/admin/microsoft365": "/configuracion/integraciones/microsoft365",
};

export function adminLegacyRedirect(path: string): string {
  return ADMIN_LEGACY_REDIRECTS[path] ?? "/configuracion";
}
