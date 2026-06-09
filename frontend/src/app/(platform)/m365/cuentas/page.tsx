"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Cloud, ArrowLeft } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api";
import { M365_STATUS_LABELS, type M365Account } from "@/lib/admin";

const REQUIRED_SCOPES = ["Mail.Read", "Mail.Send", "User.Read", "offline_access"];

export default function M365CuentasPage() {
  const [accounts, setAccounts] = useState<M365Account[]>([]);
  const [myAccount, setMyAccount] = useState<M365Account | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [list, mine] = await Promise.all([
        apiClient.getM365Accounts(),
        apiClient.getMyM365Account(),
      ]);
      setAccounts(list.items);
      setMyAccount(mine);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handlePrepare = async () => {
    await apiClient.prepareM365Account({});
    load();
  };

  return (
    <AppShell
      title="Cuentas Microsoft 365"
      description="Preparación para conectar el correo de cada usuario (sin Graph real en esta fase)"
    >
      <Link href="/m365" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4">
        <ArrowLeft className="h-4 w-4" /> Volver a Microsoft 365
      </Link>

      <Card className="mb-6 border-blue-500/20">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Cloud className="h-4 w-4" /> Mi cuenta M365
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading ? (
            <p className="text-sm text-muted-foreground">Cargando…</p>
          ) : myAccount ? (
            <>
              <div className="grid sm:grid-cols-2 gap-2 text-sm">
                <p><span className="text-muted-foreground">Usuario JAIOS:</span> {myAccount.jaios_user_name}</p>
                <p><span className="text-muted-foreground">Correo M365:</span> {myAccount.email ?? "Pendiente"}</p>
                <p><span className="text-muted-foreground">Estado:</span> {M365_STATUS_LABELS[myAccount.connection_status] ?? myAccount.connection_status}</p>
                <p><span className="text-muted-foreground">Última sincronización:</span> {myAccount.last_sync_at ? new Date(myAccount.last_sync_at).toLocaleString("es-DO") : "—"}</p>
              </div>
              <p className="text-xs text-muted-foreground">Permisos requeridos (futuro): {REQUIRED_SCOPES.join(", ")}</p>
              <div className="flex gap-2">
                <Button size="sm" disabled title="Disponible en fase posterior">
                  Conectar mi cuenta
                </Button>
                <Button size="sm" variant="outline" disabled title="Disponible en fase posterior">
                  Desconectar
                </Button>
              </div>
            </>
          ) : (
            <>
              <p className="text-sm text-muted-foreground">Tu cuenta M365 aún no está preparada en JAIOS.</p>
              <Button size="sm" onClick={handlePrepare}>Preparar mi cuenta M365</Button>
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle className="text-base">Cuentas del tenant</CardTitle></CardHeader>
        <CardContent>
          {accounts.length === 0 ? (
            <p className="text-sm text-muted-foreground">Sin cuentas preparadas.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted-foreground border-b">
                  <th className="pb-2">Usuario</th>
                  <th className="pb-2">Correo M365</th>
                  <th className="pb-2">Estado</th>
                  <th className="pb-2">Sincronización</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((a) => (
                  <tr key={a.id} className="border-b border-border/50">
                    <td className="py-2">{a.jaios_user_name}</td>
                    <td className="py-2 text-muted-foreground">{a.email ?? "—"}</td>
                    <td className="py-2">{M365_STATUS_LABELS[a.connection_status] ?? a.connection_status}</td>
                    <td className="py-2 text-muted-foreground">{a.last_sync_at ? new Date(a.last_sync_at).toLocaleString("es-DO") : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      <p className="mt-4 text-xs text-muted-foreground">
        Fase actual: solo estructura administrativa. No se leen, envían ni mueven correos reales.
      </p>
    </AppShell>
  );
}
