"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Cloud, ArrowLeft, Mail, AlertCircle } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api";
import { M365_STATUS_LABELS, type M365Account } from "@/lib/admin";

export default function M365CuentasPage() {
  const [accounts, setAccounts] = useState<M365Account[]>([]);
  const [myAccount, setMyAccount] = useState<M365Account | null>(null);
  const [loading, setLoading] = useState(true);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [imapHost, setImapHost] = useState("outlook.office365.com");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [list, mine] = await Promise.all([
        apiClient.getM365Accounts(),
        apiClient.getMyM365Account(),
      ]);
      setAccounts(list.items);
      setMyAccount(mine);
      if (mine?.email) {
        setEmail((prev) => prev || mine.email || "");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handlePrepare = async () => {
    setError(null);
    await apiClient.prepareM365Account({});
    await load();
  };

  const handleConnect = async () => {
    if (!email.trim() || !password) {
      setError("Ingresa correo y contraseña.");
      return;
    }
    setConnecting(true);
    setError(null);
    try {
      await apiClient.connectM365Imap({
        email: email.trim(),
        password,
        imap_host: imapHost.trim() || undefined,
      });
      setPassword("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo conectar el buzón.");
    } finally {
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    setConnecting(true);
    setError(null);
    try {
      await apiClient.disconnectM365Mailbox();
      setPassword("");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo desconectar.");
    } finally {
      setConnecting(false);
    }
  };

  const connected = myAccount?.mailbox_connected ?? false;

  return (
    <AppShell
      title="Cuentas Microsoft 365"
      description="Conecta tu buzón como cliente de correo — usuario y contraseña, sin configurar Azure"
    >
      <Link
        href="/m365"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground mb-4"
      >
        <ArrowLeft className="h-4 w-4" /> Volver a Microsoft 365
      </Link>

      <Card className="mb-6 border-blue-500/20">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Cloud className="h-4 w-4" /> Mi buzón de correo
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {loading ? (
            <p className="text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <>
              {myAccount && (
                <div className="grid sm:grid-cols-2 gap-2 text-sm">
                  <p>
                    <span className="text-muted-foreground">Usuario JAIOS:</span>{" "}
                    {myAccount.jaios_user_name}
                  </p>
                  <p>
                    <span className="text-muted-foreground">Estado:</span>{" "}
                    {connected
                      ? "Conectado (IMAP)"
                      : M365_STATUS_LABELS[myAccount.connection_status] ?? myAccount.connection_status}
                  </p>
                  <p>
                    <span className="text-muted-foreground">Correo:</span>{" "}
                    {myAccount.email ?? "Pendiente"}
                  </p>
                  <p>
                    <span className="text-muted-foreground">Última sincronización:</span>{" "}
                    {myAccount.last_sync_at
                      ? new Date(myAccount.last_sync_at).toLocaleString("es-DO")
                      : "—"}
                  </p>
                </div>
              )}

              {!myAccount && (
                <p className="text-sm text-muted-foreground">
                  Prepara tu perfil M365 en JAIOS antes de conectar el buzón.
                </p>
              )}

              {!connected && (
                <div className="space-y-3 rounded-lg border border-border/80 p-4">
                  <p className="text-sm font-medium flex items-center gap-2">
                    <Mail className="h-4 w-4" /> Conectar con correo y contraseña
                  </p>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="space-y-1">
                      <label className="text-xs text-muted-foreground">Correo M365</label>
                      <Input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="tu@empresa.com"
                        autoComplete="username"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs text-muted-foreground">Contraseña</label>
                      <Input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Contraseña o contraseña de aplicación"
                        autoComplete="current-password"
                      />
                    </div>
                    <div className="space-y-1 sm:col-span-2">
                      <label className="text-xs text-muted-foreground">Servidor IMAP (opcional)</label>
                      <Input
                        value={imapHost}
                        onChange={(e) => setImapHost(e.target.value)}
                        placeholder="outlook.office365.com"
                      />
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground flex items-start gap-2">
                    <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                    Si tienes MFA, crea una contraseña de aplicación en Microsoft y úsala aquí.
                    IMAP debe estar habilitado en tu buzón.
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {!myAccount && (
                      <Button size="sm" variant="outline" onClick={() => void handlePrepare()}>
                        Preparar mi cuenta
                      </Button>
                    )}
                    <Button size="sm" onClick={() => void handleConnect()} disabled={connecting}>
                      {connecting ? "Conectando…" : "Conectar buzón"}
                    </Button>
                  </div>
                </div>
              )}

              {connected && (
                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => void handleDisconnect()}
                    disabled={connecting}
                  >
                    Desconectar buzón
                  </Button>
                  <Link href="/m365/operativo">
                    <Button size="sm">Ir a bandeja operativa</Button>
                  </Link>
                </div>
              )}

              {error && <p className="text-sm text-destructive">{error}</p>}
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Cuentas del tenant</CardTitle>
        </CardHeader>
        <CardContent>
          {accounts.length === 0 ? (
            <p className="text-sm text-muted-foreground">Sin cuentas registradas.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted-foreground border-b">
                  <th className="pb-2">Usuario</th>
                  <th className="pb-2">Correo</th>
                  <th className="pb-2">Modo</th>
                  <th className="pb-2">Estado</th>
                  <th className="pb-2">Sincronización</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((a) => (
                  <tr key={a.id} className="border-b border-border/50">
                    <td className="py-2">{a.jaios_user_name}</td>
                    <td className="py-2 text-muted-foreground">{a.email ?? "—"}</td>
                    <td className="py-2 text-muted-foreground">
                      {a.mailbox_connected ? "IMAP" : a.connection_mode}
                    </td>
                    <td className="py-2">
                      {a.mailbox_connected
                        ? "Conectado"
                        : M365_STATUS_LABELS[a.connection_status] ?? a.connection_status}
                    </td>
                    <td className="py-2 text-muted-foreground">
                      {a.last_sync_at ? new Date(a.last_sync_at).toLocaleString("es-DO") : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      <p className="mt-4 text-xs text-muted-foreground">
        No necesitas registrar una app en Azure. JAIOS se conecta a tu buzón vía IMAP con tus credenciales,
        cifradas en el servidor.
      </p>
    </AppShell>
  );
}
